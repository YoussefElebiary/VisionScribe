document.addEventListener('DOMContentLoaded', function() {
    const imgBox = document.querySelector('.img-box');
    const imgText = document.querySelector('.img-text');
    const imgCaption = document.querySelector('.img-caption');
    const imgBtn = document.getElementById('img-btn');
    const clearBtn = document.getElementById('clear-btn');
    let selectedFile = null;

    // Drag and drop functionality
    imgBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        imgBox.style.borderColor = '#1a73e8';
        imgBox.style.backgroundColor = '#f0f7ff';
    });

    imgBox.addEventListener('dragleave', () => {
        imgBox.style.borderColor = '#dadce0';
        imgBox.style.backgroundColor = 'white';
    });

    imgBox.addEventListener('drop', (e) => {
        e.preventDefault();
        imgBox.style.borderColor = '#dadce0';
        imgBox.style.backgroundColor = 'white';
        
        if (e.dataTransfer.files.length) {
            handleImageUpload(e.dataTransfer.files[0]);
        }
    });

    // Click to upload functionality
    imgBox.addEventListener('click', () => {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.onchange = (e) => {
            if (e.target.files.length) {
                handleImageUpload(e.target.files[0]);
            }
        };
        fileInput.click();
    });

    // Button click handler
    imgBtn.addEventListener('click', () => {
        if (selectedFile) {
            generateCaption(selectedFile);
        } else {
            alert('Please upload an image first');
        }
    });

    clearBtn.addEventListener('click', clearImage);

    function clearImage() {
        imgBox.style.backgroundImage = '';
        imgCaption.textContent = '';
        imgCaption.style.visibility = 'hidden';
        selectedFile = null;
        imgText.style.visibility = 'visible';
        imgBox.style.cursor = 'pointer';
        clearBtn.style.display = 'none';
    }

    function handleImageUpload(file) {
        if (!file.type.match('image.*')) {
            alert('Please upload an image file');
            return;
        }

        selectedFile = file;
        const reader = new FileReader();

        reader.onload = (e) => {
            imgBox.style.backgroundImage = `url(${e.target.result})`;
            imgBox.style.backgroundSize = 'cover';
            imgBox.style.backgroundPosition = 'center';
            imgText.style.visibility = 'hidden';

            clearBtn.style.display = 'block';
        };

        reader.readAsDataURL(file);
        imgBox.style.cursor = 'default';
    }

    async function generateCaption(imageFile) {
        imgBtn.disabled = true;
        imgBtn.textContent = 'Processing...';
        imgCaption.textContent = 'Generating caption...';
        imgCaption.style.visibility = 'visible';

        try {
            const apiUrl = 'http://localhost:5000/predict';
            
            const formData = new FormData();
            formData.append('image', imageFile);

            const response = await fetch(apiUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            imgCaption.textContent = result.caption || 'Caption generated successfully';
        } catch (error) {
            console.error('Error:', error);
            imgCaption.textContent = 'Error generating caption. Please try again.';
        } finally {
            imgBtn.disabled = false;
            imgBtn.textContent = 'Describe';
        }
    }
});