document.addEventListener('DOMContentLoaded', function () {

    const moveItemModal = document.getElementById('move-item-modal');
    const modalCloseBtn = moveItemModal ? moveItemModal.querySelector('.modal-close-btn') : null;
    const modalItemNameDisplay = moveItemModal ? document.getElementById('modal-item-name-display') : null;
    const modalFolderListContainer = moveItemModal ? document.getElementById('modal-folder-list-container') : null;
    const modalMoveConfirmBtn = moveItemModal ? document.getElementById('modal-move-confirm-btn') : null;
    const modalMoveCancelBtn = moveItemModal ? document.getElementById('modal-move-cancel-btn') : null;
    const openMoveModalButtons = document.querySelectorAll('.open-move-modal-btn');

    let itemsToProcessInModal = [];
    let selectedDestinationPathInModal = null;

    /**
     * Updates the enabled/disabled state of the modal's confirm button.
     * The button is enabled only if a destination folder has been selected.
     */
    function updateModalConfirmButtonState() {
        if (!modalMoveConfirmBtn) return;
        modalMoveConfirmBtn.disabled = selectedDestinationPathInModal === null;
    }

    /**
     * Opens the move modal for a single item.
     * @param {string} itemPath - The path of the item to be moved.
     * @param {string} itemName - The display name of the item.
     */
    function openSingleItemMoveModal(itemPath, itemName) {
        if (!moveItemModal || !modalItemNameDisplay) return;
        itemsToProcessInModal = [itemPath];
        modalItemNameDisplay.textContent = `Item: ${itemName}`;
        openModalSharedLogic();
    }

    /**
     * Opens the move modal for multiple items. This function is exposed globally
     * so it can be called from other scripts (e.g., bulk actions script).
     * @param {string[]} itemPathsList - An array of paths for the items to be moved.
     * @global
     */
    window.openMoveModalForItems = function(itemPathsList) {
        if (!moveItemModal || !modalItemNameDisplay) return;
        if (!itemPathsList || itemPathsList.length === 0) {
            console.warn("No items provided to openMoveModalForItems");
            return;
        }
        itemsToProcessInModal = itemPathsList;
        modalItemNameDisplay.textContent = `${itemPathsList.length} item(s) selected`;
        openModalSharedLogic();
    }

    /**
     * Contains shared logic for opening the move modal, whether for single or multiple items.
     * Resets modal state, displays loading text for the folder list, shows the modal,
     * and initiates fetching of the folder list.
     */
    function openModalSharedLogic() {
        selectedDestinationPathInModal = null;
        if (modalFolderListContainer) modalFolderListContainer.innerHTML = '<p class="loading-text">Loading folders...</p>';
        if (moveItemModal) moveItemModal.style.display = 'block';
        populateModalFolderList();
        updateModalConfirmButtonState();
    }

    /**
     * Closes the move item modal and resets its state.
     */
    function closeMoveItemModal() {
        if (!moveItemModal) return;
        moveItemModal.style.display = 'none';
        itemsToProcessInModal = []; 
        selectedDestinationPathInModal = null; 
    }

    /**
     * Handles the selection of a folder within the modal's folder tree.
     * Updates the `selectedDestinationPathInModal` and visually highlights the selected folder.
     * @param {HTMLLIElement} selectedLiElement - The list item element that was clicked.
     * @param {string} folderPath - The path of the selected folder.
     */
    function handleFolderSelectionInModal(selectedLiElement, folderPath) {
        if (!modalFolderListContainer) return;
        selectedDestinationPathInModal = folderPath;

        modalFolderListContainer.querySelectorAll('li.folder-item').forEach(li => li.classList.remove('selected'));
        if (selectedLiElement) {
             selectedLiElement.classList.add('selected');
        }
        updateModalConfirmButtonState();
    }
    
    /**
     * Recursively creates list item elements for the folder tree display in the modal.
     * Each folder can be expanded/collapsed if it has children.
     * @param {object} folderData - Data for the folder, including name, path, and children.
     * @param {string} folderData.name - The display name of the folder.
     * @param {string} folderData.path - The relative path of the folder.
     * @param {object[]} folderData.children - An array of child folder data objects.
     * @param {boolean} [isRootPseudoFolder=false] - Flag to indicate if this is the virtual "Root" folder.
     * @returns {HTMLLIElement} The created list item element representing the folder.
     */
    function createFolderListItem(folderData, isRootPseudoFolder = false) {
        const li = document.createElement('li');
        li.classList.add('folder-item');
        li.dataset.path = folderData.path;

        const contentWrapper = document.createElement('div');
        contentWrapper.classList.add('folder-content-wrapper');

        const toggleIcon = document.createElement('i');
        toggleIcon.classList.add('fas', 'folder-toggle-icon');
        if ((isRootPseudoFolder && folderData.children && folderData.children.length > 0) || (!isRootPseudoFolder && folderData.children && folderData.children.length > 0)) {
            toggleIcon.classList.add('fa-caret-right');
        } else {
            toggleIcon.classList.add('no-children');
        }

        const folderIconElement = document.createElement('i');
        folderIconElement.classList.add('fas', isRootPseudoFolder ? 'fa-hdd' : 'fa-folder', 'folder-icon-tree');

        const folderNameSpan = document.createElement('span');
        folderNameSpan.classList.add('folder-name');
        folderNameSpan.textContent = folderData.name;

        contentWrapper.appendChild(toggleIcon);
        contentWrapper.appendChild(folderIconElement);
        contentWrapper.appendChild(folderNameSpan);
        li.appendChild(contentWrapper);

        contentWrapper.addEventListener('click', (event) => {
            event.stopPropagation();
            handleFolderSelectionInModal(li, folderData.path);
        });

        if (folderData.children && folderData.children.length > 0) {
            const subList = document.createElement('ul');
            subList.classList.add('subfolder-list');
            subList.style.display = 'none';

            folderData.children.forEach(childFolder => {
                subList.appendChild(createFolderListItem(childFolder));
            });
            li.appendChild(subList);

            toggleIcon.addEventListener('click', (event) => {
                event.stopPropagation();
                const isExpanded = subList.style.display === 'block';
                subList.style.display = isExpanded ? 'none' : 'block';
                toggleIcon.classList.toggle('fa-caret-right', isExpanded);
                toggleIcon.classList.toggle('fa-caret-down', !isExpanded);
                li.classList.toggle('expanded', !isExpanded);
            });
        }
        return li;
    }

    /**
     * Fetches the folder tree structure from the server API and populates the modal's list.
     * Displays loading and error messages as appropriate.
     * A "Root" pseudo-folder is added to allow moving items to the base directory.
     */
    function populateModalFolderList() {
        if (!modalFolderListContainer) return;
        if (typeof listFoldersTreeApiUrl === 'undefined') { 
            modalFolderListContainer.innerHTML = '<p class="loading-text">Error: Tree API URL not configured.</p>';
            console.error("listFoldersTreeApiUrl is not defined. Check index.html script block.");
            return;
        }

        fetch(listFoldersTreeApiUrl)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error ${response.status} fetching folder tree.`);
                return response.json();
            })
            .then(folderTreeData => {
                if (folderTreeData.error) {
                    console.error('Error from server fetching folder tree:', folderTreeData.error);
                    modalFolderListContainer.innerHTML = `<p class="loading-text">Error loading folders: ${folderTreeData.error}</p>`;
                    return;
                }

                modalFolderListContainer.innerHTML = '';
                const ul = document.createElement('ul');
                ul.classList.add('top-level-folder-list');

                const rootPseudoFolder = {
                    name: 'Root',
                    path: '',
                    children: folderTreeData,
                    depth: 0 
                };
                ul.appendChild(createFolderListItem(rootPseudoFolder, true));

                modalFolderListContainer.appendChild(ul);
            })
            .catch(error => {
                console.error('Failed to fetch or populate folder tree for move:', error);
                modalFolderListContainer.innerHTML = `<p class="loading-text">Failed to load folders. ${error.message}</p>`;
            });
    }


    if (moveItemModal) {
        openMoveModalButtons.forEach(button => {
            button.addEventListener('click', function() {
                const itemPath = this.dataset.itemPath;
                const itemName = this.dataset.itemName;
                openSingleItemMoveModal(itemPath, itemName);
            });
        });

        if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeMoveItemModal);
        if (modalMoveCancelBtn) modalMoveCancelBtn.addEventListener('click', closeMoveItemModal);
        window.addEventListener('click', function(event) {
            if (event.target === moveItemModal) closeMoveItemModal();
        });

        if (modalMoveConfirmBtn) {
            modalMoveConfirmBtn.addEventListener('click', function() {
                /**
                 * Handles the click event for the modal's "Confirm Move" button.
                 * Validates that items and a destination are selected.
                 * Sends a POST request to the server API to move the items.
                 * Reloads the page on success, shows an alert on error.
                 */
                if (itemsToProcessInModal.length === 0 || selectedDestinationPathInModal === null) {
                    alert('No items to move or no destination folder selected.');
                    return;
                }
    
                if (typeof moveMultipleItemsApiUrl === 'undefined') {
                    console.error("moveMultipleItemsApiUrl is not defined. Check index.html script block.");
                    alert("Error: Move action URL not configured."); // User-facing error
                    return;
                }
                const moveUrl = moveMultipleItemsApiUrl;
    
                const payload = {
                    items_to_move: itemsToProcessInModal,
                    destination_path: selectedDestinationPathInModal
                };
    
                fetch(moveUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
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
                    closeMoveItemModal();
                    setTimeout(() => { 
                        window.location.reload();
                    }, 200); 
                })
                .catch(error => {
                    console.error('[move_modal.js] Final error moving items:', error);
                    alert(`Error moving items: ${error.message}`);
                });
            });
        }
    }
});