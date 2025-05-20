document.addEventListener('DOMContentLoaded', function () {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const bulkActionsContainer = document.getElementById('bulk-actions-container');
    const bulkActionsSummary = document.getElementById('bulk-actions-summary');
    const downloadSelectedZipBtn = document.getElementById('download-selected-zip-btn');

    function updateBulkActionsVisibility() {
        const selectedCheckboxes = Array.from(itemCheckboxes).filter(cb => cb.checked);
        const anyChecked = selectedCheckboxes.length > 0;

        if (bulkActionsContainer) {
            bulkActionsContainer.style.display = anyChecked ? 'block' : 'none';
        }

        if (selectAllCheckbox) {
            if (!anyChecked) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            } else if (selectedCheckboxes.length === itemCheckboxes.length) {
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;
            } else {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = true;
            }
        }
    }

    function getFormattedDateTime() {
        const now = new Date();
        const year = now.getFullYear();
        const month = (now.getMonth() + 1).toString().padStart(2, '0');
        const day = now.getDate().toString().padStart(2, '0');
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const seconds = now.getSeconds().toString().padStart(2, '0');
        return `${year}-${month}-${day}_${hours}-${minutes}-${seconds}`;
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            itemCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateBulkActionsVisibility();
        });
    }

    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            updateBulkActionsVisibility();
        });
    });

    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', function () {
            const selectedItemsPaths = Array.from(itemCheckboxes)
                .filter(checkbox => checkbox.checked)
                .map(checkbox => checkbox.value);

            const selectedItemsNames = Array.from(itemCheckboxes)
                .filter(checkbox => checkbox.checked)
                .map(checkbox => checkbox.dataset.name);

            if (selectedItemsPaths.length === 0) {
                alert('Please select at least one item to remove.');
                return;
            }

            const confirmationMessage = `Are you sure you want to delete the following ${selectedItemsPaths.length} element(s)?:\n\n${selectedItemsNames.slice(0, 10).join('\n')}${selectedItemsPaths.length > 10 ? '\n...y ' + (selectedItemsPaths.length - 10) + ' más.' : ''}\n\nTHIS ACTION IS IRREVERSIBLE.`;

            if (confirm(confirmationMessage)) {
                const deleteUrl = deleteSelectedBtn.dataset.deleteUrl;
                if (!deleteUrl) {
                    alert('Error: The URL for the delete action could not be found.');
                    return;
                }

                bulkActionsSummary.innerHTML = '<p>Processing elimination...</p>';

                fetch(deleteUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ items_to_delete: selectedItemsPaths })
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(errData => {
                            throw new Error(errData.message || `Server error: ${response.status}`);
                        }).catch(() => {
                            throw new Error(`Server error: ${response.status} ${response.statusText}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    let summaryHtml = '<h4>Result of the elimination:</h4><ul>';
                    if (data.details && Array.isArray(data.details)) {
                        data.details.forEach(detail => {
                            summaryHtml += `<li style="color: ${detail.success ? 'green' : 'red'};"><strong>${detail.item_name}</strong>: ${detail.message}</li>`;
                        });
                    }
                    summaryHtml += '</ul>';
                    if (data.overall_success) {
                         summaryHtml += '<p style="color: green;">All selected items were processed correctly.</p>';
                    } else {
                         summaryHtml += '<p style="color: orange;">Some elements could not be removed or no longer existed..</p>';
                    }
                    bulkActionsSummary.innerHTML = summaryHtml;

                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                })
                .catch(error => {
                    console.error('Error in multiple elimination:', error);
                    bulkActionsSummary.innerHTML = `<p style="color: red;">Error during operation: ${error.message}</p>`;
                });
            }
        });
    }

    if (downloadSelectedZipBtn) {
        downloadSelectedZipBtn.addEventListener('click', function() {
            const selectedItemsPaths = Array.from(itemCheckboxes)
                .filter(checkbox => checkbox.checked)
                .map(checkbox => checkbox.value);

            if (selectedItemsPaths.length === 0) {
                alert('Please select at least one file to include in the ZIP.');
                return;
            }

            const timestamp = getFormattedDateTime();
            const zipFileName = `files_${timestamp}.zip`;

            const downloadUrl = downloadSelectedZipBtn.dataset.downloadZipUrl;
            if (!downloadUrl) {
                alert('Error: The URL for the download action could not be found.');
                return;
            }

            bulkActionsSummary.innerHTML = `<p>Preparing ZIP file: '${zipFileName}'...</p>`;

            fetch(downloadUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    items_to_download: selectedItemsPaths, 
                    zip_name: zipFileName
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errData => {
                        throw new Error(errData.message || `Server error: ${response.status}`);
                    }).catch(() => {
                        throw new Error(`Server error: ${response.status} ${response.statusText}`);
                    });
                }
                const disposition = response.headers.get('Content-Disposition');
                let effectiveFilename = zipFileName;
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) {
                        effectiveFilename = matches[1].replace(/['"]/g, '');
                    }
                }
                return response.blob().then(blob => ({ blob, filename: effectiveFilename }));
            })
            .then(({ blob, filename }) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                
                window.URL.revokeObjectURL(url);
                a.remove();
                
                bulkActionsSummary.innerHTML = `<p style="color: green;">Download of '${filename}' initiated.</p>`;
                itemCheckboxes.forEach(cb => cb.checked = false);
                if(selectAllCheckbox) selectAllCheckbox.checked = false;
                updateBulkActionsVisibility();
            })
            .catch(error => {
                console.error('Error downloading multiple files as ZIP:', error);
                bulkActionsSummary.innerHTML = `<p style="color: red;">Download error: ${error.message}</p>`;
            });
        });
    }
    updateBulkActionsVisibility();
});