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
    const reviewReadyContainer = document.getElementById('review-ready-container');
    const errorContainer = document.getElementById('error-container');
    const errorText = document.getElementById('error-text');
    const downloadMdBtn = document.getElementById('download-md-btn');
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    const resetBtn = document.getElementById('reset-btn');
    const retryBtn = document.getElementById('retry-btn');
    const openEditorBtn = document.getElementById('open-editor-btn');
    const skipEditBtn = document.getElementById('skip-edit-btn');

    // ─── Queue & Files Elements ──────────────────────────────────────────
    const queueList = document.getElementById('queue-list');
    const queueEmpty = document.getElementById('queue-empty');
    const queueCount = document.getElementById('queue-count');
    const filesList = document.getElementById('files-list');
    const filesEmpty = document.getElementById('files-empty');
    const filesCount = document.getElementById('files-count');

    // ─── Editor Elements ─────────────────────────────────────────────────
    const mainLayout = document.getElementById('main-layout');
    const editorLayout = document.getElementById('editor-layout');
    const editorBackBtn = document.getElementById('editor-back-btn');
    const editorTitle = document.getElementById('editor-title');
    const editorSaveBtn = document.getElementById('editor-save-btn');
    const editorGeneratePdfBtn = document.getElementById('editor-generate-pdf-btn');
    const mdEditor = document.getElementById('md-editor');
    const mdPreview = document.getElementById('md-preview');
    const saveIndicator = document.getElementById('save-indicator');

    let currentTaskId = null;
    let currentEditFilename = null;
    let editorReturnTo = 'main'; // 'main' or 'status'
    let pollInterval = null;
    let queuePollInterval = null;
    let previewDebounceTimer = null;

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
            reviewReadyContainer.classList.add('hidden');
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
                showSuccess(data);
                fetchFiles();
                fetchQueue();
            } else if (data.status === 'Review Ready') {
                clearInterval(pollInterval);
                showReviewReady(data);
                fetchFiles();
                fetchQueue();
            } else if (data.status === 'Error' || data.status === 'PDF Error') {
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

    function showSuccess(data) {
        statusContainer.classList.add('hidden');
        reviewReadyContainer.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        if (data && data.output_basename) {
            downloadMdBtn.href = `/download/${encodeURIComponent(data.output_basename)}.md`;
            downloadPdfBtn.href = `/download/${encodeURIComponent(data.output_basename)}.pdf`;
        } else {
            downloadMdBtn.href = `/download/md/${currentTaskId}`;
            downloadPdfBtn.href = `/download/pdf/${currentTaskId}`;
        }
    }

    function showReviewReady(data) {
        statusContainer.classList.add('hidden');
        resultContainer.classList.add('hidden');
        errorContainer.classList.add('hidden');
        reviewReadyContainer.classList.remove('hidden');

        // Store the basename for editor
        if (data && data.output_basename) {
            reviewReadyContainer.dataset.filename = data.output_basename;
        }
    }

    function showError(message) {
        statusContainer.classList.add('hidden');
        uploadSection.classList.add('hidden');
        statusSection.classList.remove('hidden');
        reviewReadyContainer.classList.add('hidden');
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
        reviewReadyContainer.classList.add('hidden');
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

    // ─── Review Ready Handlers ───────────────────────────────────────────

    openEditorBtn.addEventListener('click', () => {
        const filename = reviewReadyContainer.dataset.filename;
        if (filename) {
            editorReturnTo = 'status';
            openEditor(filename);
        }
    });

    skipEditBtn.addEventListener('click', async () => {
        const filename = reviewReadyContainer.dataset.filename;
        if (filename) {
            await triggerPdfGeneration(filename);
        }
    });

    // ─── Markdown Editor ─────────────────────────────────────────────────

    async function openEditor(filename) {
        currentEditFilename = filename;

        // Load content
        try {
            const response = await fetch(`/files/${encodeURIComponent(filename)}/content`);
            if (!response.ok) throw new Error('Failed to load file');
            const data = await response.json();

            mdEditor.value = data.content;
            editorTitle.textContent = `Editing: ${filename}`;
            updatePreview();

            // Show editor, hide main
            mainLayout.classList.add('hidden');
            editorLayout.classList.remove('hidden');
            saveIndicator.classList.add('hidden');

        } catch (error) {
            console.error('Error loading file:', error);
            showError('Failed to load file for editing.');
        }
    }

    function closeEditor() {
        editorLayout.classList.add('hidden');
        mainLayout.classList.remove('hidden');
        currentEditFilename = null;

        // Refresh files list
        fetchFiles();

        if (editorReturnTo === 'status') {
            // Check if task completed (PDF generated) while editing
            if (currentTaskId) {
                pollInterval = setInterval(checkStatus, 2000);
                checkStatus();
            }
        }
        editorReturnTo = 'main';
    }

    function updatePreview() {
        if (typeof marked !== 'undefined') {
            mdPreview.innerHTML = marked.parse(mdEditor.value);
        } else {
            // Fallback: show raw text
            mdPreview.textContent = mdEditor.value;
        }
    }

    // Live preview on typing (debounced)
    mdEditor.addEventListener('input', () => {
        clearTimeout(previewDebounceTimer);
        previewDebounceTimer = setTimeout(updatePreview, 200);
    });

    // Save button
    editorSaveBtn.addEventListener('click', async () => {
        if (!currentEditFilename) return;

        editorSaveBtn.disabled = true;
        try {
            const response = await fetch(`/files/${encodeURIComponent(currentEditFilename)}/content`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: mdEditor.value }),
            });

            if (!response.ok) throw new Error('Save failed');

            // Show saved indicator
            saveIndicator.classList.remove('hidden');
            setTimeout(() => saveIndicator.classList.add('hidden'), 2000);
        } catch (error) {
            console.error('Error saving:', error);
        } finally {
            editorSaveBtn.disabled = false;
        }
    });

    // Generate PDF from editor
    editorGeneratePdfBtn.addEventListener('click', async () => {
        if (!currentEditFilename) return;

        // Save first, then generate
        editorGeneratePdfBtn.disabled = true;
        editorGeneratePdfBtn.textContent = 'Saving & Generating...';

        try {
            // Save content
            await fetch(`/files/${encodeURIComponent(currentEditFilename)}/content`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: mdEditor.value }),
            });

            // Trigger PDF generation
            await triggerPdfGeneration(currentEditFilename);

            // Close editor, go back to status view
            closeEditor();

        } catch (error) {
            console.error('Error generating PDF:', error);
        } finally {
            editorGeneratePdfBtn.disabled = false;
            editorGeneratePdfBtn.textContent = 'Generate PDF';
        }
    });

    // Back button
    editorBackBtn.addEventListener('click', closeEditor);

    // ─── PDF Generation ──────────────────────────────────────────────────

    async function triggerPdfGeneration(filename) {
        try {
            const response = await fetch(`/files/${encodeURIComponent(filename)}/convert`, {
                method: 'POST',
            });

            if (!response.ok) throw new Error('Convert failed');

            // If we have an active task, resume polling for completion
            if (currentTaskId) {
                statusContainer.classList.remove('hidden');
                reviewReadyContainer.classList.add('hidden');
                statusText.textContent = 'Generating PDF...';
                pollInterval = setInterval(checkStatus, 2000);
            }

            fetchFiles();
        } catch (error) {
            console.error('Error triggering PDF generation:', error);
            showError('Failed to start PDF generation.');
        }
    }

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
            if (file.converting) {
                downloadButtons += `
                    <span class="file-converting-badge" title="Generating PDF...">⏳</span>
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
                    <button class="file-edit-btn" title="Edit markdown" data-filename="${escapeHtml(file.filename)}">✏️</button>
                    ${downloadButtons}
                    ${!file.has_pdf && !file.converting ? `<button class="file-convert-btn" title="Generate PDF" data-filename="${escapeHtml(file.filename)}">📄→PDF</button>` : ''}
                </div>
                <button class="file-delete-btn" title="Delete file" data-filename="${escapeHtml(file.filename)}">🗑</button>
            `;

            // Edit button
            row.querySelector('.file-edit-btn').addEventListener('click', () => {
                editorReturnTo = 'main';
                openEditor(file.filename);
            });

            // Convert button (if present)
            const convertBtn = row.querySelector('.file-convert-btn');
            if (convertBtn) {
                convertBtn.addEventListener('click', async () => {
                    convertBtn.disabled = true;
                    convertBtn.textContent = '⏳';
                    await triggerPdfGeneration(file.filename);
                });
            }

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
