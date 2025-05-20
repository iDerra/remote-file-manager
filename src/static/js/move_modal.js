document.addEventListener('DOMContentLoaded', function () {
    const bulkActionsSummary = document.getElementById('bulk-actions-summary');

    const moveItemModal = document.getElementById('move-item-modal');
    const modalCloseBtn = moveItemModal ? moveItemModal.querySelector('.modal-close-btn') : null;
    const modalItemNameDisplay = moveItemModal ? document.getElementById('modal-item-name-display') : null;
    const modalFolderListContainer = moveItemModal ? document.getElementById('modal-folder-list-container') : null;
    const modalMoveConfirmBtn = moveItemModal ? document.getElementById('modal-move-confirm-btn') : null;
    const modalMoveCancelBtn = moveItemModal ? document.getElementById('modal-move-cancel-btn') : null;
    const openMoveModalButtons = document.querySelectorAll('.open-move-modal-btn');

    let selectedDestinationPathInModal = null;
    let itemsToProcessInModal = [];

    function updateModalConfirmButtonState() {
        if (!modalMoveConfirmBtn) return;
        if (selectedDestinationPathInModal !== null) {
            modalMoveConfirmBtn.disabled = false;
        } else {
            modalMoveConfirmBtn.disabled = true;
        }
    }
    
    function openSingleItemMoveModal(itemPath, itemName) {
        if (!moveItemModal || !modalItemNameDisplay || !modalFolderListContainer) return;
        itemsToProcessInModal = [itemPath];
        modalItemNameDisplay.textContent = `Item: ${itemName}`;
        selectedDestinationPathInModal = null;
        modalFolderListContainer.innerHTML = '<p class="loading-text">Loading folders...</p>';
        moveItemModal.style.display = 'block';
        populateModalFolderList();
        updateModalConfirmButtonState();
    }

    window.openMoveModalForItems = function(itemPathsList) {
        if (!moveItemModal || !modalItemNameDisplay || !modalFolderListContainer) return;
        if (!itemPathsList || itemPathsList.length === 0) {
            console.warn("No items provided to openMoveModalForItems");
            return;
        }
        itemsToProcessInModal = itemPathsList;
        modalItemNameDisplay.textContent = `${itemPathsList.length} item(s) selected`;
        selectedDestinationPathInModal = null;
        modalFolderListContainer.innerHTML = '<p class="loading-text">Loading folders...</p>';
        moveItemModal.style.display = 'block';
        populateModalFolderList();
        updateModalConfirmButtonState();
    }

    function closeMoveItemModal() {
        if (!moveItemModal) return;
        moveItemModal.style.display = 'none';
        currentMovingItemPath = null;
        selectedDestinationPathInModal = null;
    }

    function populateModalFolderList() {
        if (!modalFolderListContainer) return;
        if (typeof listFoldersApiUrl === 'undefined') {
            modalFolderListContainer.innerHTML = '<p class="loading-text">Error: API URL not configured.</p>';
            console.error("listFoldersApiUrl is not defined. Make sure to define it in your HTML before loading this script.");
            return;
        }

        fetch(listFoldersApiUrl)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error ${response.status} fetching folder list.`);
                return response.json();
            })
            .then(folderList => {
                if (folderList.error) {
                    console.error('Error from server fetching folder list:', folderList.error);
                    modalFolderListContainer.innerHTML = `<p class="loading-text">Error loading folders: ${folderList.error}</p>`;
                    return;
                }

                modalFolderListContainer.innerHTML = ''; 
                const ul = document.createElement('ul');

                const rootLi = document.createElement('li');
                rootLi.textContent = 'Root';
                rootLi.dataset.path = ""; 
                rootLi.addEventListener('click', function() {
                    handleFolderSelectionInModal(this, "");
                });
                ul.appendChild(rootLi);

                folderList.forEach(folder => {
                    const li = document.createElement('li');
                    li.textContent = folder.display; 
                    li.dataset.path = folder.path;
                    li.addEventListener('click', function() {
                        handleFolderSelectionInModal(this, folder.path);
                    });
                    ul.appendChild(li);
                });
                modalFolderListContainer.appendChild(ul);
            })
            .catch(error => {
                console.error('Failed to fetch or populate folder list for move:', error);
                modalFolderListContainer.innerHTML = `<p class="loading-text">Failed to load folders. ${error.message}</p>`;
            });
    }

    function handleFolderSelectionInModal(selectedLiElement, folderPath) {
        if (!modalFolderListContainer) return;
        selectedDestinationPathInModal = folderPath;

        const allLis = modalFolderListContainer.querySelectorAll('li');
        allLis.forEach(li => li.classList.remove('selected'));

        selectedLiElement.classList.add('selected');
        updateModalConfirmButtonState();
    }

    if (moveItemModal) { 
        openMoveModalButtons.forEach(button => {
            button.addEventListener('click', function() {
                const itemPath = this.dataset.itemPath;
                const itemName = this.dataset.itemName;
                openSingleItemMoveModal(itemPath, itemName);
            });
        });

        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', closeMoveItemModal);
        }
        if (modalMoveCancelBtn) {
            modalMoveCancelBtn.addEventListener('click', closeMoveItemModal);
        }

        window.addEventListener('click', function(event) {
            if (event.target === moveItemModal) {
                closeMoveItemModal();
            }
        });

        if (modalMoveConfirmBtn) {
            modalMoveConfirmBtn.addEventListener('click', function() {
                if (itemsToProcessInModal.length === 0 || selectedDestinationPathInModal === null) {
                    alert('No items to move or no destination folder selected.');
                    return;
                }

                if (typeof moveMultipleItemsApiUrl === 'undefined') {
                    console.error("moveMultipleItemsApiUrl is not defined. Make sure to define it in your HTML.");
                    if(bulkActionsSummary) bulkActionsSummary.innerHTML = `<p style="color: red;">Error: Move action URL not configured.</p>`;
                    return;
                }
                const moveMultipleUrl = moveMultipleItemsApiUrl;
        
                const payload = {
                    items_to_move: itemsToProcessInModal,
                    destination_path: selectedDestinationPathInModal
                };

                if(bulkActionsSummary) bulkActionsSummary.innerHTML = `<p>Moving ${itemsToProcessInModal.length} item(s)...</p>`;

                fetch(moveMultipleUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
                })
                .then(response => {
                    if (!response.ok) {
                         return response.json().then(errData => {
                            let serverMessage = 'Unknown server error';
                            if (errData && errData.message) {
                                serverMessage = errData.message;
                            } else if (errData && errData.details) {
                                serverMessage = errData.details.map(d => `${d.item_name || 'Item'}: ${d.message}`).join('; ');
                            }
                            throw new Error(serverMessage || `Server error: ${response.status}`);
                        }).catch(() => {
                            throw new Error(`Server error: ${response.status} ${response.statusText}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    let summaryHtml = `<h4>Result of move operation:</h4>`;

                    if (data.message) {
                        summaryHtml += `<p>${data.message}</p>`;
                    }

                    let successfulMoves = 0;
                    let totalProcessed = 0;

                    if (data.details && Array.isArray(data.details)) {
                        totalProcessed = data.details.length;
                        data.details.forEach(detail => {
                            if (detail.success) {
                                successfulMoves++;
                            }
                        });

                        if (totalProcessed > 0) {
                            if (data.overall_success && successfulMoves === totalProcessed) {
                                summaryHtml += `<p style="color: green;">${successfulMoves} of ${totalProcessed} item(s) processed successfully.</p>`;
                            } else if (successfulMoves > 0 && successfulMoves < totalProcessed) {
                                summaryHtml += `<p style="color: orange;">${successfulMoves} of ${totalProcessed} item(s) moved successfully. Some items may have failed.</p>`;
                            } else if (successfulMoves === 0 && totalProcessed > 0 && !data.overall_success) {
                                summaryHtml += `<p style="color: red;">0 of ${totalProcessed} item(s) were moved. Check server logs if message above is not clear.</p>`;
                            }
                        }
                    } else if (data.overall_success) {
                        summaryHtml += `<p style="color: green;">Operation completed successfully.</p>`;
                    } else if (data.overall_success === false && !data.message) {
                        summaryHtml += `<p style="color: red;">Operation failed with no specific details.</p>`;
                    }

                    if(bulkActionsSummary) bulkActionsSummary.innerHTML = summaryHtml;

                    if (data.overall_success !== false) {
                         setTimeout(() => {
                            window.location.reload();
                        }, data.details && data.details.length > 5 ? 4000 : 2000);
                    }
                    closeMoveItemModal();
                })
                .catch(error => {
                    console.error('Error moving items:', error);
                    if(bulkActionsSummary) bulkActionsSummary.innerHTML = `<p style="color: red;">Error moving items: ${error.message}</p>`;
                });
            });
        }
    } else {
        console.warn('move_modal.js: moveItemModal element NOT found when trying to attach listeners.');
    }
});