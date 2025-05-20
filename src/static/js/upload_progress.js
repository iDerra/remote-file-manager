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

    /**
     * Initializes the upload process when a file or folder upload form is submitted.
     * It prevents default form submission, validates file selection, resets and shows
     * the progress UI, and then starts uploading files one by one.
     *
     * @param {Event} event - The form submission event.
     * @param {HTMLInputElement} fileInputElement - The file input element that contains the selected files.
     */
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

        /**
         * Uploads a single file from the selected list to the server using XMLHttpRequest.
         * This function is called recursively to process all files in the list sequentially.
         * It updates the progress bar and status messages after each file upload attempt.
         *
         * @param {number} index - The index of the file to upload from the 'files' FileList.
         */
        function uploadSingleFileFromList(index) {
            if (index >= totalFiles) {
                if (uploadStatusText) uploadStatusText.textContent = 'All files processed.';
                if (progressBar) {
                    progressBar.style.width = '100%';
                    progressBar.textContent = '100%';
                }
                if (fileCountText) fileCountText.textContent = `Processed ${processedFilesCount} of ${totalFiles} files. Successful uploads: ${successfulUploadsCount}.`;
                
                setTimeout(() => { 
                    window.location.reload(); 
                }, 2000);
                return;
            }

            const currentFile = files[index];
            const formData = new FormData();
            formData.append('files_to_upload', currentFile);

            if (currentFile.webkitRelativePath) {
                formData.append('relative_path', currentFile.webkitRelativePath);
            } else {
                formData.append('relative_path', currentFile.name); 
            }

            const xhr = new XMLHttpRequest();
            xhr.open('POST', formActionUrl, true);

            xhr.onload = function() {
                processedFilesCount++;
                let fileStatusMessage = '';
                const currentFileNameForDisplay = currentFile.webkitRelativePath || currentFile.name;

                if (xhr.status === 200 || xhr.status === 201) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            successfulUploadsCount++;
                            fileStatusMessage = `<li>${currentFileNameForDisplay}: ${response.message}</li>`;
                        } else {
                            fileStatusMessage = `<li style="color: red;">${response.filename || currentFileNameForDisplay}: ${response.message || 'Unknown server error'}</li>`;
                        }
                    } catch (e) {
                        fileStatusMessage = `<li style="color: red;">${currentFileNameForDisplay}: Error processing server response. ${e.message}</li>`;
                    }
                } else {
                    let serverErrorMsg = `Upload error (HTTP ${xhr.status} ${xhr.statusText})`;
                    try {
                        const errResponse = JSON.parse(xhr.responseText);
                        if(errResponse && errResponse.message) serverErrorMsg = errResponse.message;
                    } catch(e) { /* ignore */ }
                    fileStatusMessage = `<li style="color: red;">${currentFileNameForDisplay}: ${serverErrorMsg}</li>`;
                }
                
                if (individualFileStatusList) individualFileStatusList.innerHTML += fileStatusMessage;

                const overallPercent = (processedFilesCount / totalFiles) * 100;
                if (progressBar) {
                    progressBar.style.width = overallPercent.toFixed(0) + '%';
                    progressBar.textContent = overallPercent.toFixed(0) + '%';
                }
                if (fileCountText) fileCountText.textContent = `Processed ${processedFilesCount} of ${totalFiles} files...`;
                if (uploadStatusText) uploadStatusText.textContent = `Processing: ${currentFileNameForDisplay}...`;

                uploadSingleFileFromList(index + 1);
            };

            xhr.onerror = function() {
                processedFilesCount++;
                const currentFileNameForDisplay = currentFile.webkitRelativePath || currentFile.name;
                const fileStatusMessage = `<li style="color: red;">${currentFileNameForDisplay}: Network or connection error.</li>`;
                if (individualFileStatusList) individualFileStatusList.innerHTML += fileStatusMessage;
                
                const overallPercent = (processedFilesCount / totalFiles) * 100;
                if (progressBar) {
                    progressBar.style.width = overallPercent.toFixed(0) + '%';
                    progressBar.textContent = overallPercent.toFixed(0) + '%';
                }
                if (fileCountText) fileCountText.textContent = `Processed ${processedFilesCount} of ${totalFiles} files...`;

                uploadSingleFileFromList(index + 1);
            };
            
            xhr.send(formData);
        }

        uploadSingleFileFromList(0);
    }

    if (uploadFilesForm && filesInputForFiles) {
        uploadFilesForm.addEventListener('submit', function(event) {
            initializeUploadProcess(event, filesInputForFiles);
        });
    } else {
        console.warn("Could not find 'upload-files-form' or 'files-upload-input-files'. File upload functionality might be affected.");
    }
    
    if (uploadFolderForm && filesInputForFolder) {
        uploadFolderForm.addEventListener('submit', function(event) {
            initializeUploadProcess(event, filesInputForFolder);
        });
    } else {
        console.warn("Could not find 'upload-folder-form' or 'files-upload-input-folder'. Folder upload functionality might be affected.");
    }
});