document.addEventListener('DOMContentLoaded', function () {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const bulkActionsContainer = document.getElementById('bulk-actions-container');
    const downloadSelectedZipBtn = document.getElementById('download-selected-zip-btn');
    const moveSelectedBtn = document.getElementById('move-selected-btn');


    const pendingDownloadUrl = sessionStorage.getItem('pendingDownloadUrl');
    const pendingDownloadName = sessionStorage.getItem('pendingDownloadName');

    /**
     * Checks for and triggers a download if its URL and name are found in session storage.
     * This is used to initiate a download after a page reload (e.g., after preparing a ZIP).
     * The download information is then cleared from session storage.
     */
    if (pendingDownloadUrl && pendingDownloadName) {
        console.log("Pending download found:", pendingDownloadName, "URL:", pendingDownloadUrl);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = pendingDownloadUrl;
        a.download = pendingDownloadName;
        document.body.appendChild(a);
        try {
            a.click();
            console.log("Download triggered for:", pendingDownloadName);
        } catch (e) {
            console.error("Error triggering download automatically:", e);
            alert(`Could not automatically start download for ${pendingDownloadName}. Please try the download link if provided, or check browser settings.`);
        }
        
        setTimeout(() => {
            if (document.body.contains(a)) {
                 document.body.removeChild(a);
            }
            sessionStorage.removeItem('pendingDownloadUrl');
            sessionStorage.removeItem('pendingDownloadName');
            console.log("Pending download info cleared from session storage.");
        }, 1000);
    }

    /**
     * Updates the visibility of the bulk actions container and the state
     * of the "select all" checkbox based on how many item checkboxes are selected.
     * - Shows bulk actions if any item is checked.
     * - Hides bulk actions if no items are checked.
     * - Sets "select all" to checked if all items are checked.
     * - Sets "select all" to indeterminate if some (but not all) items are checked.
     * - Sets "select all" to unchecked if no items are checked.
     */
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

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            /**
             * Handles the change event of the "select all" checkbox.
             * Checks or unchecks all item checkboxes based on the "select all" state
             * and then updates the visibility of bulk actions.
             */
            itemCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateBulkActionsVisibility();
        });
    }

    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            /**
             * Handles the change event of an individual item checkbox.
             * Updates the visibility of bulk actions.
             */
            updateBulkActionsVisibility();
        });
    });

    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', function () {
            /**
             * Handles the click event for the "Delete Selected" button.
             * Gathers all selected item paths and their display names.
             * Prompts the user for confirmation before sending a POST request
             * to the server to delete the items. Reloads the page on success.
             * Displays an error message on failure.
             */
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

            const confirmationMessage = `Are you sure you want to delete the following ${selectedItemsPaths.length} element(s)?:\n\n${selectedItemsNames.slice(0, 10).join('\n')}${selectedItemsPaths.length > 10 ? '\n...and ' + (selectedItemsPaths.length - 10) + ' more.' : ''}\n\nTHIS ACTION IS IRREVERSIBLE.`;

            if (confirm(confirmationMessage)) {
                const deleteUrl = deleteSelectedBtn.dataset.deleteUrl;
                if (!deleteUrl) {
                    alert('Error: The URL for the delete action could not be found.');
                    return;
                }

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
                            let serverMessage = `Server error: ${response.status} ${response.statusText}`;
                            if (errData && errData.message) serverMessage = errData.message;
                            throw new Error(serverMessage);
                        }).catch((e) => {
                            if (e instanceof Error && e.message.startsWith("Server error:")) throw e;
                            throw new Error(`Server error: ${response.status} ${response.statusText}. Could not parse error details.`);
                        });
                    }
                    return response.json(); 
                })
                .then(data => {
                    window.location.reload();
                })
                .catch(error => {
                    console.error('Error in multiple deletion:', error);
                    alert(`Error during operation: ${error.message}`);
                });
            }
        });
    }

    if (downloadSelectedZipBtn) {
        downloadSelectedZipBtn.addEventListener('click', function() {
            /**
             * Handles the click event for the "Download Selected as ZIP" button.
             * Gathers paths of selected items and sends a POST request to a server endpoint
             * to prepare a ZIP file. If successful, stores download URL and name in
             * session storage and reloads the page to trigger the download.
             */
            const selectedItemsPaths = Array.from(itemCheckboxes)
                .filter(checkbox => checkbox.checked)
                .map(checkbox => checkbox.value);

            if (selectedItemsPaths.length === 0) {
                alert('Please select at least one file to include in the ZIP.');
                return;
            }

            const zipFileNameSuggestion = "download.zip";

            if (typeof prepareZipApiUrl === 'undefined') {
                alert('Error: Prepare ZIP API URL not configured.');
                console.error("prepareZipApiUrl is not defined. Check index.html script block.");
                return;
            }
            const prepareUrl = prepareZipApiUrl;

            fetch(prepareUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    items_to_download: selectedItemsPaths, 
                    zip_name: zipFileNameSuggestion
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errData => {
                        let serverMessage = `Server error: ${response.status} ${response.statusText}`;
                        if (errData && errData.message) serverMessage = errData.message;
                        throw new Error(serverMessage);
                    }).catch((e) => {
                        if (e instanceof Error && e.message.startsWith("Server error:")) throw e;
                        throw new Error(`Server error: ${response.status} ${response.statusText}. Could not parse error details.`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success && data.download_url && data.zip_display_name) {
                    sessionStorage.setItem('pendingDownloadUrl', data.download_url);
                    sessionStorage.setItem('pendingDownloadName', data.zip_display_name);
                    window.location.reload();
                } else {
                    alert(data.message || 'Failed to prepare ZIP file for download.');
                }
            })
            .catch(error => {
                console.error('Error preparing multiple files for ZIP download:', error);
                alert(`Error preparing download: ${error.message}`);
            });
        });
    }

    if (moveSelectedBtn) {
        moveSelectedBtn.addEventListener('click', function() {
            /**
             * Handles the click event for the "Move Selected" button.
             * Gathers paths of selected items and calls a globally available function
             * `window.openMoveModalForItems` to open a modal for selecting the
             * destination for the move operation.
             */
            const selectedItemsPaths = Array.from(itemCheckboxes)
                .filter(checkbox => checkbox.checked)
                .map(checkbox => checkbox.value);

            if (selectedItemsPaths.length === 0) {
                alert('Please select at least one item to move.');
                return;
            }
            if (typeof window.openMoveModalForItems === 'function') {
                window.openMoveModalForItems(selectedItemsPaths);
            } else {
                console.error('Move modal function (openMoveModalForItems) is not available. Make sure move_modal.js is loaded and the function is globally exposed.');
                alert('Error: Move functionality is not properly initialized.');
            }
        });
    }
    updateBulkActionsVisibility();
});