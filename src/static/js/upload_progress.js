document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('files-to-upload-input');
    const progressArea = document.getElementById('upload-progress-area');
    const progressBar = document.getElementById('progress-bar');
    const fileCountText = document.getElementById('file-count-text');
    const uploadStatusText = document.getElementById('upload-status-text');
    const individualFileStatusList = document.getElementById('individual-file-status');
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(event) {
            event.preventDefault();

            const files = fileInput.files;
            if (files.length === 0) {
                alert('Please select at least one file to upload.');
                return;
            }

            progressArea.style.display = 'block';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            uploadStatusText.textContent = 'Initiating upload...';
            fileCountText.textContent = `Uploading 0 of ${files.length} files...`;
            individualFileStatusList.innerHTML = '';

            let uploadedFilesCount = 0;
            let totalFiles = files.length;
            const formActionUrl = uploadForm.action;

            function uploadFile(index) {
                if (index >= totalFiles) {
                    uploadStatusText.textContent = 'All files processed.';
                    setTimeout(() => { window.location.reload(); }, 1000);
                    return;
                }

                const currentFile = files[index];
                const formData = new FormData();
                formData.append('files_to_upload', currentFile);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', formActionUrl, true);

                xhr.onload = function() {
                    let fileStatusMessage = '';
                    if (xhr.status === 200) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            if (response.success) {
                                uploadedFilesCount++;
                                fileStatusMessage = `<li>${response.filename}: ${response.message} (Success)</li>`;
                            } else {
                                fileStatusMessage = `<li style="color: red;">${response.filename || currentFile.name}: ${response.message} (Error)</li>`;
                            }
                        } catch (e) {
                                fileStatusMessage = `<li style="color: red;">${currentFile.name}: Error processing server response.</li>`;
                        }
                    } else {
                        fileStatusMessage = `<li style="color: red;">${currentFile.name}: Upload error (HTTP ${xhr.status}).</li>`;
                    }
                    
                    individualFileStatusList.innerHTML += fileStatusMessage;

                    const overallPercent = (uploadedFilesCount / totalFiles) * 100;
                    progressBar.style.width = overallPercent.toFixed(2) + '%';
                    progressBar.textContent = overallPercent.toFixed(2) + '%';
                    fileCountText.textContent = `Uploaded ${uploadedFilesCount} of ${totalFiles} files...`;
                    uploadStatusText.textContent = `Processing file: ${currentFile.name}...`;

                    uploadFile(index + 1);
                };

                xhr.onerror = function() {
                    const fileStatusMessage = `<li style="color: red;">${currentFile.name}: Network or connection error during upload.</li>`;
                    individualFileStatusList.innerHTML += fileStatusMessage;
                    uploadFile(index + 1);
                };
                
                xhr.send(formData);
            }

            uploadFile(0);
        });
    }
});