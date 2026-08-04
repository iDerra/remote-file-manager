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

    function updateModalConfirmButtonState() {
        if (!modalMoveConfirmBtn) return;
        modalMoveConfirmBtn.disabled = selectedDestinationPathInModal === null;
    }

    // Extrae la ruta de la carpeta padre para que el modal se abra allí
    function getParentPath(path) {
        const lastSlashIndex = path.lastIndexOf('/');
        if (lastSlashIndex === -1) return ''; // Raíz
        return path.substring(0, lastSlashIndex);
    }

    function openSingleItemMoveModal(itemPath, itemName) {
        if (!moveItemModal || !modalItemNameDisplay) return;
        itemsToProcessInModal = [itemPath];
        modalItemNameDisplay.textContent = `Item: ${itemName}`;
        
        let initialPath = getParentPath(itemPath);
        openModalSharedLogic(initialPath);
    }

    window.openMoveModalForItems = function(itemPathsList) {
        if (!moveItemModal || !modalItemNameDisplay) return;
        if (!itemPathsList || itemPathsList.length === 0) return;
        itemsToProcessInModal = itemPathsList;
        modalItemNameDisplay.textContent = `${itemPathsList.length} item(s) selected`;
        
        let initialPath = getParentPath(itemPathsList[0]);
        openModalSharedLogic(initialPath);
    }

    function openModalSharedLogic(initialPath) {
        selectedDestinationPathInModal = null;
        if (modalFolderListContainer) modalFolderListContainer.innerHTML = '<p class="loading-text">Cargando...</p>';
        if (moveItemModal) moveItemModal.style.display = 'block';
        
        loadFoldersLazy(initialPath);
    }

    function closeMoveItemModal() {
        if (!moveItemModal) return;
        moveItemModal.style.display = 'none';
        itemsToProcessInModal = [];
        selectedDestinationPathInModal = null;
    }

    function loadFoldersLazy(path) {
        if (!modalFolderListContainer) return;
        modalFolderListContainer.innerHTML = '<p class="loading-text"><i class="fas fa-spinner fa-spin"></i> Explorando...</p>';
        
        fetch('/api/folders-lazy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                modalFolderListContainer.innerHTML = `<p class="loading-text" style="color: red;">Error: ${data.error}</p>`;
                return;
            }
            
            // La carpeta que se visualiza se selecciona automáticamente como destino
            selectedDestinationPathInModal = data.current_path;
            updateModalConfirmButtonState();
            
            modalFolderListContainer.innerHTML = '';
            
            const pathHeader = document.createElement('div');
            pathHeader.style.padding = '10px';
            pathHeader.style.fontWeight = 'bold';
            pathHeader.style.backgroundColor = '#f8f9fa';
            pathHeader.style.borderBottom = '1px solid #dee2e6';
            pathHeader.style.marginBottom = '5px';
            pathHeader.innerHTML = `<i class="fas fa-bullseye" style="color:#007bff; margin-right:5px;"></i> Destino: /${data.current_path}`;
            modalFolderListContainer.appendChild(pathHeader);

            const ul = document.createElement('ul');
            ul.classList.add('top-level-folder-list');
            ul.style.listStyle = 'none';
            ul.style.padding = '0';
            ul.style.margin = '0';

            // Opción para ir a la carpeta anterior
            if (data.parent_path !== null) {
                const li = document.createElement('li');
                li.classList.add('folder-item');
                li.innerHTML = '<div class="folder-content-wrapper" style="padding: 10px; cursor: pointer; border-bottom: 1px solid #e9ecef;"><i class="fas fa-level-up-alt folder-icon-tree" style="margin-right:8px; color:#6c757d;"></i><span class="folder-name font-weight-bold" style="color:#6c757d;">.. (Carpeta anterior)</span></div>';
                li.addEventListener('click', () => loadFoldersLazy(data.parent_path));
                ul.appendChild(li);
            }

            // Opciones de subcarpetas
            data.folders.forEach(folder => {
                const li = document.createElement('li');
                li.classList.add('folder-item');
                li.innerHTML = `<div class="folder-content-wrapper" style="padding: 10px; cursor: pointer; border-bottom: 1px solid #e9ecef;"><i class="fas fa-folder folder-icon-tree" style="margin-right:8px; color:#FFD700;"></i><span class="folder-name">${folder.name}</span></div>`;
                li.addEventListener('click', () => loadFoldersLazy(folder.path));
                ul.appendChild(li);
            });

            if (data.folders.length === 0 && data.parent_path === null) {
               const li = document.createElement('li');
               li.innerHTML = '<div style="padding: 10px; color: #888;">Directorio vacío</div>';
               ul.appendChild(li);
            }

            modalFolderListContainer.appendChild(ul);
        })
        .catch(error => {
            modalFolderListContainer.innerHTML = `<p class="loading-text" style="color: red;">Error de red: ${error.message}</p>`;
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
                if (itemsToProcessInModal.length === 0 || selectedDestinationPathInModal === null) {
                    alert('No items to move or no destination folder selected.');
                    return;
                }
                
                if (typeof moveMultipleItemsApiUrl === 'undefined') {
                    alert("Error: Move action URL not configured.");
                    return;
                }
                
                const payload = {
                    items_to_move: itemsToProcessInModal,
                    destination_path: selectedDestinationPathInModal
                };
                
                fetch(moveMultipleItemsApiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(errData => {
                            throw new Error(errData.message || `Server error: ${response.status}`);
                        }).catch(e => {
                            throw new Error(e.message || `Server error: ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    closeMoveItemModal();
                    setTimeout(() => window.location.reload(), 200);
                })
                .catch(error => {
                    alert(`Error moving items: ${error.message}`);
                });
            });
        }
    }
});