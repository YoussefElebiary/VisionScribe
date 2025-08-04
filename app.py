from flask import Flask, render_template, request, jsonify    # For the back-end
from flask_cors import CORS
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.inception_v3 import InceptionV3
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, LSTM, Embedding, add
from tensorflow.keras.layers import Flatten, Dropout, BatchNormalization
import pickle
from PIL import Image
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

def preprocess_image(image_bytes):
    """Convert bytes to PIL Image, resize, and preprocess for InceptionV3"""
    try:
        # Convert bytes to PIL Image
        img = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if needed (handles PNG with alpha channel)
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Resize to 299x299 for InceptionV3
        img = img.resize((299, 299))
        
        # Convert to numpy array and preprocess
        img_array = np.array(img)
        img_array = img_array / 255.0
        img_array = img_array - 0.5
        img_array = img_array * 2.0
        
        # Add batch dimension
        return np.expand_dims(img_array, axis=0)
        
    except Exception as e:
        print(f"Error preprocessing image: {str(e)}")
        raise


def extract_image_features(model, image_path):
    img = preprocess_image(image_path)
    features = model.predict(img, verbose=0)
    return features

def build_model(vocab_size, max_caption_length, cnn_output_dim):
    input_image = Input(shape=(cnn_output_dim,), name='Features_Input')
    fe1 = BatchNormalization()(input_image)
    fe2 = Dense(256, activation='relu')(fe1)
    fe3 = BatchNormalization()(fe2)

    input_caption = Input(shape=(max_caption_length,), name='Sequence_Input')
    se1 = Embedding(vocab_size, 256, mask_zero=True)(input_caption)
    se2 = LSTM(256)(se1)

    decoder1 = add([fe3, se2])
    decoder2 = Dense(256, activation='relu')(decoder1)
    outputs = Dense(vocab_size, activation='softmax', name='Output_Layer')(decoder2)

    model = Model(inputs=[input_image, input_caption], outputs=outputs)
    return model

def beam_search_generator(model, image_features, K_beams=3, log=False):
    start = [TOKENIZER.word_index['start']]
    start_word = [[start, 0.0]]
    for _ in range(25):
        temp = []
        for s in start_word:
            sequence = pad_sequences([s[0]], maxlen=25, padding='post')
            preds = model.predict([image_features.reshape(1, 2048), sequence], verbose=0)
            word_preds = np.argsort(preds[0])[-K_beams:]
            for w in word_preds:
                next_cap, prob = s[0][:], s[1]
                next_cap.append(w)
                prob += np.log(preds[0][w]) if log else preds[0][w]
                temp.append([next_cap, prob])
        start_word = sorted(temp, key=lambda l: l[1], reverse=True)[:K_beams]

    final_sequence = start_word[0][0]
    captions_ = [TOKENIZER.index_word.get(i, '') for i in final_sequence]
    final_caption = []
    for word in captions_:
        if word == 'end':
            break
        final_caption.append(word)
    return ' '.join(final_caption[1:])

TOKENIZER = None
MODEL = None

inception_v3_model = InceptionV3(weights = 'imagenet', input_shape=(299, 299, 3))
inception_v3_model.layers.pop()
inception_v3_model = Model(inputs=inception_v3_model.inputs, outputs=inception_v3_model.layers[-2].output)

with open("./models/tokenizer.pkl", "rb") as f:
    TOKENIZER = pickle.load(f)

MODEL = build_model(len(TOKENIZER.word_index) + 1, 25, 2048)
MODEL.load_weights('./models/caption_model.weights.h5')

# Creating flask app
app = Flask(__name__)
CORS(app, resources={
    r"/predict": {
        "origins": ["http://127.0.0.1:5000", "http://localhost:5000"],
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        # Handle preflight request
        response = jsonify({'status': 'preflight'})
        response.headers.add('Access-Control-Allow-Origin', 'http://127.0.0.1:5000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    
    try:
        image_file = request.files['image'].read()
        processed_image = preprocess_image(image_file)
        features = inception_v3_model.predict(processed_image)
        
        caption = beam_search_generator(MODEL, features, K_beams=3, log=True)
        return jsonify({"caption": caption.capitalize()}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()