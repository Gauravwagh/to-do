/**
 * Selection Manager
 * Multi-select with checkboxes and keyboard shortcuts
 */

let selectedItems = new Map(); // id -> {type, element}

/**
 * Toggle selection
 */
function toggleSelection(event, itemId, itemType) {
    event.stopPropagation();

    const card = event.target.closest('.folder-card, .file-card');
    if (!card) return;

    if (event.target.checked) {
        // Select
        selectedItems.set(itemId, { type: itemType, element: card });
        card.classList.add('selected');
    } else {
        // Deselect
        selectedItems.delete(itemId);
        card.classList.remove('selected');
    }

    updateSelectionUI();
}

/**
 * Select all items
 */
function selectAll() {
    document.querySelectorAll('.folder-card, .file-card').forEach(card => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (checkbox && !checkbox.checked) {
            checkbox.checked = true;
            const itemId = card.dataset.itemId;
            const itemType = card.dataset.itemType;
            selectedItems.set(itemId, { type: itemType, element: card });
            card.classList.add('selected');
        }
    });

    updateSelectionUI();
}

/**
 * Clear selection
 */
function clearSelection() {
    selectedItems.forEach((item, id) => {
        item.element.classList.remove('selected');
        const checkbox = item.element.querySelector('input[type="checkbox"]');
        if (checkbox) checkbox.checked = false;
    });

    selectedItems.clear();
    updateSelectionUI();
}

/**
 * Update selection UI
 */
function updateSelectionUI() {
    const count = selectedItems.size;
    const toolbar = document.getElementById('bulkActionsToolbar');
    const countSpan = document.getElementById('selectedCount');

    if (count > 0) {
        toolbar.classList.add('active');
        countSpan.textContent = `${count} selected`;
        document.body.classList.add('selection-mode');
    } else {
        toolbar.classList.remove('active');
        document.body.classList.remove('selection-mode');
    }
}

/**
 * Bulk move
 */
function bulkMove() {
    if (selectedItems.size === 0) return;

    // Prepare data for move modal
    const documentIds = [];
    const folderIds = [];

    selectedItems.forEach((item, id) => {
        if (item.type === 'document') {
            documentIds.push(id);
        } else if (item.type === 'folder') {
            folderIds.push(id);
        }
    });

    // Store in form
    document.getElementById('bulkMoveDocumentIds').value = JSON.stringify(documentIds);
    document.getElementById('bulkMoveFolderIds').value = JSON.stringify(folderIds);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('bulkMoveModal'));
    modal.show();
}

/**
 * Bulk delete
 */
function bulkDelete() {
    if (selectedItems.size === 0) return;

    const count = selectedItems.size;
    if (!confirm(`Are you sure you want to delete ${count} item(s)?`)) {
        return;
    }

    performBulkDelete();
}

/**
 * Perform bulk delete via API
 */
async function performBulkDelete() {
    const documentIds = [];
    const folderIds = [];

    selectedItems.forEach((item, id) => {
        if (item.type === 'document') {
            documentIds.push(id);
        } else if (item.type === 'folder') {
            folderIds.push(id);
        }
    });

    try {
        showLoading();

        // Delete documents
        if (documentIds.length > 0) {
            const response = await fetch('/api/v1/documents/documents/bulk_operations/', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    document_ids: documentIds,
                    action: 'delete'
                })
            });

            if (!response.ok) {
                throw new Error('Failed to delete documents');
            }
        }

        // Delete folders
        for (const folderId of folderIds) {
            const response = await fetch(`/api/v1/documents/categories/${folderId}/`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete folder');
            }
        }

        showToast('Items deleted successfully!', 'success');

        // Refresh page
        setTimeout(() => window.location.reload(), 500);

    } catch (error) {
        console.error('Error deleting items:', error);
        showToast('Error: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}
