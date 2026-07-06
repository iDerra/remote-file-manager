document.addEventListener('DOMContentLoaded', function() {
    const uploadFilesForm = document.getElementById('upload-files-form');
    const uploadFolderForm = document.getElementById('upload-folder-form');

    const filesInputForFiles = document.getElementById('files-upload-input-files');
    const filesInputForFolder = document.getElementById('files-upload-input-folder');

    const progressContainer = document.getElementById('upload-progress-container');
    const progressArea = document.getElementById('upload-progress-area');
    const progressBar = document.getElementById('progress-bar');
    const fileCountText = document.getElementById('file-count-text');
    const uploadStatusText = document.getElementById('upload-status-text');
    const individualFileStatusList = document.getElementById('individual-file-status');

    // OPTIMIZACIÓN 1: Subimos el trozo a 50 MB para reducir la carga del disco duro
    const CHUNK_SIZE = 50 * 1024 * 1024; 

    // Función auxiliar para formatear la velocidad
    function formatSpeed(bytesPerSecond) {
        if (bytesPerSecond >= 1048576) return (bytesPerSecond / 1048576).toFixed(2) + ' MB/s';
        if (bytesPerSecond >= 1024) return (bytesPerSecond / 1024).toFixed(2) + ' KB/s';
        return bytesPerSecond.toFixed(0) + ' B/s';
    }

    function initializeUploadProcess(event, fileInputElement) {
        event.preventDefault();

        const files = fileInputElement.files;
        if (files.length === 0) {
            alert('Please select at least one file or a folder to upload.');
            return;
        }

        if (progressContainer) progressContainer.style.display = 'block';
        if (progressArea) progressArea.style.display = 'block';

        if (progressBar) {
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
        }
        if (uploadStatusText) uploadStatusText.textContent = 'Initiating upload...';
        if (fileCountText) fileCountText.textContent = `Processing 0 of ${files.length} files...`;
        if (individualFileStatusList) individualFileStatusList.innerHTML = '';

        let processedFilesCount = 0;
        let successfulUploadsCount = 0;
        const totalFiles = files.length;
        const formActionUrl = event.target.action;

        function uploadSingleFileFromList(index) {
            if (index >= totalFiles) {
                if (uploadStatusText) uploadStatusText.textContent = 'All files processed.';
                if (progressBar) {
                    progressBar.style.width = '100%';
                    progressBar.textContent = '100%';
                }
                if (fileCountText) fileCountText.textContent = `Processed ${processedFilesCount} of ${totalFiles} files. Successful uploads: ${successfulUploadsCount}.`;
                
                setTimeout(() => { window.location.reload(); }, 2000);
                return;
            }

            const currentFile = files[index];
            const totalChunks = Math.ceil(currentFile.size / CHUNK_SIZE);
            const currentFileNameForDisplay = currentFile.webkitRelativePath || currentFile.name;
            
            let currentChunk = 0;
            let fileStartTime = Date.now(); // Iniciamos el cronómetro

            function uploadChunk() {
                const start = currentChunk * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, currentFile.size);
                const chunk = currentFile.slice(start, end);

                const formData = new FormData();
                formData.append('files_to_upload', chunk, currentFile.name);
                formData.append('relative_path', currentFileNameForDisplay);
                
                if (totalChunks > 1) {
                    formData.append('chunk_index', currentChunk);
                    formData.append('total_chunks', totalChunks);
                }

                const xhr = new XMLHttpRequest();
                xhr.open('POST', formActionUrl, true);

                xhr.onload = function() {
                    if (xhr.status === 200 || xhr.status === 201 || xhr.status === 206) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            if (response.success) {
                                if (xhr.status === 206) {
                                    currentChunk++;
                                    
                                    // CALCULADORA DE VELOCIDAD
                                    const elapsedTime = (Date.now() - fileStartTime) / 1000; // Segundos
                                    const bytesUploaded = currentChunk * CHUNK_SIZE;
                                    const speed = bytesUploaded / elapsedTime; // Bytes por segundo
                                    const fileProgress = (currentChunk / totalChunks) * 100;
                                    
                                    if (uploadStatusText) {
                                        uploadStatusText.innerHTML = `Uploading <strong>${currentFileNameForDisplay}</strong>: ${fileProgress.toFixed(0)}% <span style="color:#0d6efd; margin-left: 10px;"><i class="fas fa-tachometer-alt"></i> ${formatSpeed(speed)}</span>`;
                                    }
                                    
                                    uploadChunk(); 
                                } else {
                                    successfulUploadsCount++;
                                    finishFileUpload(index, `<li style="color: green;">${currentFileNameForDisplay}: ${response.message}</li>`);
                                }
                            } else {
                                finishFileUpload(index, `<li style="color: red;">${currentFileNameForDisplay}: ${response.message}</li>`);
                            }
                        } catch (e) {
                            finishFileUpload(index, `<li style="color: red;">${currentFileNameForDisplay}: Error processing server response. ${e.message}</li>`);
                        }
                    } else {
                        let serverErrorMsg = `Upload error (HTTP ${xhr.status})`;
                        try {
                            const errResponse = JSON.parse(xhr.responseText);
                            if(errResponse && errResponse.message) serverErrorMsg = errResponse.message;
                        } catch(e) {}
                        finishFileUpload(index, `<li style="color: red;">${currentFileNameForDisplay}: ${serverErrorMsg}</li>`);
                    }
                };

                xhr.onerror = function() {
                    finishFileUpload(index, `<li style="color: red;">${currentFileNameForDisplay}: Network or connection error.</li>`);
                };

                xhr.send(formData);
            }

            if (uploadStatusText) uploadStatusText.textContent = `Starting: ${currentFileNameForDisplay}...`;
            uploadChunk();
        }

        function finishFileUpload(index, statusMessageHtml) {
            processedFilesCount++;
            if (individualFileStatusList) individualFileStatusList.innerHTML += statusMessageHtml;

            const overallPercent = (processedFilesCount / totalFiles) * 100;
            if (progressBar) {
                progressBar.style.width = overallPercent.toFixed(0) + '%';
                progressBar.textContent = overallPercent.toFixed(0) + '%';
            }
            if (fileCountText) fileCountText.textContent = `Processed ${processedFilesCount} of ${totalFiles} files...`;

            uploadSingleFileFromList(index + 1);
        }

        uploadSingleFileFromList(0);
    }

    if (uploadFilesForm && filesInputForFiles) {
        uploadFilesForm.addEventListener('submit', function(event) {
            initializeUploadProcess(event, filesInputForFiles);
        });
    }
    if (uploadFolderForm && filesInputForFolder) {
        uploadFolderForm.addEventListener('submit', function(event) {
            initializeUploadProcess(event, filesInputForFolder);
        });
    }
});