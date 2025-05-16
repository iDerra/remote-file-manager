document.addEventListener('DOMContentLoaded', function () {
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const bulkActionsContainer = document.getElementById('bulk-actions-container');
    const bulkActionsSummary = document.getElementById('bulk-actions-summary');

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
    updateBulkActionsVisibility();
});