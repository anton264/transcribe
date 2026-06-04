document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const uploadSection = document.getElementById('upload-section');
    const statusSection = document.getElementById('status-section');
    const fileDropArea = document.getElementById('file-drop-area');
    const fileInput = document.getElementById('audio_file');
    const fileMessage = document.querySelector('.file-message');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('span');
    const btnSpinner = document.getElementById('btn-spinner');
    
    const statusContainer = document.querySelector('.status-container');
    const statusText = document.getElementById('status-text');
    const resultContainer = document.getElementById('result-container');
    const errorContainer = document.getElementById('error-container');
    const errorText = document.getElementById('error-text');
    const downloadMdBtn = document.getElementById('download-md-btn');
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    const resetBtn = document.getElementById('reset-btn');
    const retryBtn = document.getElementById('retry-btn');

    let currentTaskId = null;
    let pollInterval = null;

    // File drag and drop visual effects
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => {
            fileDropArea.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => {
            fileDropArea.classList.remove('dragover');
        }, false);
    });

    fileDropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length) {
            fileInput.files = files;
            updateFileMessage();
        }
    }

    fileInput.addEventListener('change', updateFileMessage);

    function updateFileMessage() {
        if (fileInput.files.length > 0) {
            const fileName = fileInput.files[0].name;
            fileMessage.textContent = `Selected: ${fileName}`;
            fileMessage.style.color = 'var(--accent-primary)';
            fileMessage.style.fontWeight = '600';
        } else {
            fileMessage.textContent = 'Drag & drop your audio file here or click to browse';
            fileMessage.style.color = 'var(--text-secondary)';
            fileMessage.style.fontWeight = 'normal';
        }
    }

    // Form submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (fileInput.files.length === 0) return;

        // UI state update
        btnText.textContent = 'Uploading...';
        btnSpinner.classList.remove('hidden');
        submitBtn.disabled = true;

        const formData = new FormData(uploadForm);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();
            currentTaskId = data.task_id;
            
            // Switch to status section
            uploadSection.classList.add('hidden');
            statusSection.classList.remove('hidden');
            statusContainer.classList.remove('hidden');
            resultContainer.classList.add('hidden');
            errorContainer.classList.add('hidden');
            
            // Start polling
            pollInterval = setInterval(checkStatus, 2000);

        } catch (error) {
            console.error('Error:', error);
            showError('Failed to upload file. Please try again.');
        } finally {
            // Reset button state
            btnText.textContent = 'Process Audio';
            btnSpinner.classList.add('hidden');
            submitBtn.disabled = false;
        }
    });

    // Polling function
    async function checkStatus() {
        if (!currentTaskId) return;

        try {
            const response = await fetch(`/status/${currentTaskId}`);
            const data = await response.json();

            if (data.status === 'Completed') {
                clearInterval(pollInterval);
                showSuccess();
            } else if (data.status === 'Error') {
                clearInterval(pollInterval);
                showError(data.error || 'An unknown error occurred during processing.');
            } else {
                // Update status text
                statusText.textContent = data.status;
            }
        } catch (error) {
            console.error('Error checking status:', error);
            // Don't stop polling on single network failure, let it retry
        }
    }

    function showSuccess() {
        statusContainer.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        downloadMdBtn.href = `/download/md/${currentTaskId}`;
        downloadPdfBtn.href = `/download/pdf/${currentTaskId}`;
    }

    function showError(message) {
        statusContainer.classList.add('hidden');
        uploadSection.classList.add('hidden');
        statusSection.classList.remove('hidden');
        errorContainer.classList.remove('hidden');
        errorText.textContent = message;
    }

    // Reset buttons
    function resetApp() {
        currentTaskId = null;
        if (pollInterval) clearInterval(pollInterval);
        
        uploadForm.reset();
        updateFileMessage();
        
        uploadSection.classList.remove('hidden');
        statusSection.classList.add('hidden');
        resultContainer.classList.add('hidden');
        errorContainer.classList.add('hidden');
    }

    resetBtn.addEventListener('click', (e) => {
        e.preventDefault();
        resetApp();
    });

    retryBtn.addEventListener('click', (e) => {
        e.preventDefault();
        resetApp();
    });
});
