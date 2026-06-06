document.addEventListener('DOMContentLoaded', () => {
    // ─── Upload Form Elements ────────────────────────────────────────────
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

    // ─── Queue & Files Elements ──────────────────────────────────────────
    const queueList = document.getElementById('queue-list');
    const queueEmpty = document.getElementById('queue-empty');
    const queueCount = document.getElementById('queue-count');
    const filesList = document.getElementById('files-list');
    const filesEmpty = document.getElementById('files-empty');
    const filesCount = document.getElementById('files-count');

    let currentTaskId = null;
    let pollInterval = null;
    let queuePollInterval = null;

    // ─── File Drag & Drop ────────────────────────────────────────────────

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

    // ─── Form Submission ─────────────────────────────────────────────────

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

            // Start polling task status
            pollInterval = setInterval(checkStatus, 2000);

            // Refresh queue immediately
            fetchQueue();

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

    // ─── Task Status Polling ─────────────────────────────────────────────

    async function checkStatus() {
        if (!currentTaskId) return;

        try {
            const response = await fetch(`/status/${currentTaskId}`);
            const data = await response.json();

            if (data.status === 'Completed') {
                clearInterval(pollInterval);
                showSuccess();
                fetchFiles();
                fetchQueue();
            } else if (data.status === 'Error') {
                clearInterval(pollInterval);
                showError(data.error || 'An unknown error occurred during processing.');
                fetchQueue();
            } else if (data.status === 'Cancelled' || data.status === 'Cancelling...') {
                clearInterval(pollInterval);
                showError('Task was cancelled.');
                fetchQueue();
            } else {
                statusText.textContent = data.status;
            }
        } catch (error) {
            console.error('Error checking status:', error);
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

    // ─── Queue Management ────────────────────────────────────────────────

    async function fetchQueue() {
        try {
            const response = await fetch('/queue');
            const queue = await response.json();
            renderQueue(queue);
        } catch (error) {
            console.error('Error fetching queue:', error);
        }
    }

    function renderQueue(queue) {
        // Clear existing cards (but keep empty state element)
        const existingCards = queueList.querySelectorAll('.queue-card');
        existingCards.forEach(card => card.remove());

        queueCount.textContent = queue.length;

        if (queue.length === 0) {
            queueEmpty.classList.remove('hidden');
            return;
        }

        queueEmpty.classList.add('hidden');

        queue.forEach(item => {
            const card = document.createElement('div');
            card.className = 'queue-card';
            card.dataset.taskId = item.task_id;

            card.innerHTML = `
                <div class="queue-card-pulse"></div>
                <div class="queue-card-info">
                    <div class="queue-card-name" title="${escapeHtml(item.original_name)}">${escapeHtml(item.original_name)}</div>
                    <div class="queue-card-status">${escapeHtml(item.status)}</div>
                </div>
                <button class="queue-cancel-btn" title="Cancel task" data-task-id="${item.task_id}">✕</button>
            `;

            card.querySelector('.queue-cancel-btn').addEventListener('click', () => {
                cancelQueueItem(item.task_id, card);
            });

            queueList.appendChild(card);
        });
    }

    async function cancelQueueItem(taskId, cardElement) {
        showConfirmDialog(
            'Cancel Task',
            'Are you sure you want to cancel this task?',
            async () => {
                try {
                    const response = await fetch(`/queue/${taskId}`, { method: 'DELETE' });
                    if (response.ok) {
                        cardElement.classList.add('removing');
                        setTimeout(() => fetchQueue(), 350);
                    }
                } catch (error) {
                    console.error('Error cancelling task:', error);
                }
            }
        );
    }

    // ─── File Management ─────────────────────────────────────────────────

    async function fetchFiles() {
        try {
            const response = await fetch('/files');
            const files = await response.json();
            renderFiles(files);
        } catch (error) {
            console.error('Error fetching files:', error);
        }
    }

    function renderFiles(files) {
        // Clear existing rows (keep empty state)
        const existingRows = filesList.querySelectorAll('.file-row');
        existingRows.forEach(row => row.remove());

        filesCount.textContent = files.length;

        if (files.length === 0) {
            filesEmpty.classList.remove('hidden');
            return;
        }

        filesEmpty.classList.add('hidden');

        files.forEach(file => {
            const row = document.createElement('div');
            row.className = 'file-row';
            row.dataset.filename = file.filename;

            const sizeStr = formatFileSize(file.size_bytes);

            let downloadButtons = `
                <a href="/download/${encodeURIComponent(file.filename)}.md" class="file-download-btn md-btn" title="Download Markdown">.md</a>
            `;
            if (file.has_pdf) {
                downloadButtons += `
                    <a href="/download/${encodeURIComponent(file.filename)}.pdf" class="file-download-btn pdf-btn" title="Download PDF">.pdf</a>
                `;
            }

            row.innerHTML = `
                <div class="file-info">
                    <div class="file-name" title="${escapeHtml(file.display_name)}">${escapeHtml(file.display_name)}</div>
                    <div class="file-meta">
                        <span class="file-date">📅 ${file.date}</span>
                        <span>${sizeStr}</span>
                    </div>
                </div>
                <div class="file-actions">
                    ${downloadButtons}
                </div>
                <button class="file-delete-btn" title="Delete file" data-filename="${escapeHtml(file.filename)}">🗑</button>
            `;

            row.querySelector('.file-delete-btn').addEventListener('click', () => {
                deleteFile(file.filename, file.display_name, row);
            });

            filesList.appendChild(row);
        });
    }

    async function deleteFile(filename, displayName, rowElement) {
        showConfirmDialog(
            'Delete Document',
            `Are you sure you want to delete "${displayName}"? This cannot be undone.`,
            async () => {
                try {
                    const response = await fetch(`/files/${encodeURIComponent(filename)}`, { method: 'DELETE' });
                    if (response.ok) {
                        rowElement.classList.add('removing');
                        setTimeout(() => fetchFiles(), 350);
                    }
                } catch (error) {
                    console.error('Error deleting file:', error);
                }
            }
        );
    }

    // ─── Confirm Dialog ──────────────────────────────────────────────────

    function showConfirmDialog(title, message, onConfirm) {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';

        overlay.innerHTML = `
            <div class="confirm-dialog">
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(message)}</p>
                <div class="confirm-buttons">
                    <button class="btn secondary-btn confirm-cancel-btn">Cancel</button>
                    <button class="btn danger-btn confirm-ok-btn">Delete</button>
                </div>
            </div>
        `;

        const close = () => overlay.remove();

        overlay.querySelector('.confirm-cancel-btn').addEventListener('click', close);
        overlay.querySelector('.confirm-ok-btn').addEventListener('click', () => {
            close();
            onConfirm();
        });
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) close();
        });

        document.body.appendChild(overlay);
    }

    // ─── Utilities ───────────────────────────────────────────────────────

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // ─── Initialization ──────────────────────────────────────────────────

    // Fetch files and queue on page load
    fetchFiles();
    fetchQueue();

    // Poll queue every 3 seconds to keep it updated
    queuePollInterval = setInterval(() => {
        fetchQueue();
        // Also refresh files in case a task just completed
        fetchFiles();
    }, 3000);
});
