/**
 * Drag and Drop Manager
 * Drag files and folders to reorganize
 */

let draggedItems = [];
let draggedElement = null;

/**
 * Initialize drag and drop
 */
function initializeDragDrop() {
    // Make cards draggable
    document.querySelectorAll('.folder-card, .file-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
            handleDragStart(e, card.dataset.itemId, card.dataset.itemType);
        });
        card.addEventListener('dragend', handleDragEnd);
    });

    // Make folders and sidebar tree items drop targets
    document.querySelectorAll('.folder-card').forEach(folder => {
        folder.addEventListener('dragover', handleDragOver);
        folder.addEventListener('dragenter', handleDragEnter);
        folder.addEventListener('dragleave', handleDragLeave);
        folder.addEventListener('drop', (e) => {
            handleDrop(e, folder.dataset.itemId);
        });
    });

    // Make empty area drop target for root
    const driveContent = document.querySelector('.drive-content');
    if (driveContent) {
        driveContent.addEventListener('dragover', handleDragOver);
        driveContent.addEventListener('drop', (e) => {
            if (e.target === driveContent || e.target.closest('.empty-state')) {
                handleDrop(e, null);
            }
        });
    }
}

/**
 * Handle drag start
 */
function handleDragStart(event, itemId, itemType) {
    draggedElement = event.target;
    draggedElement.classList.add('dragging');

    // Check if item is selected
    if (selectedItems.has(itemId)) {
        // Drag all selected items
        draggedItems = Array.from(selectedItems.entries()).map(([id, item]) => ({
            id: id,
            type: item.type
        }));
    } else {
        // Drag only this item
        draggedItems = [{
            id: itemId,
            type: itemType
        }];
    }

    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', JSON.stringify(draggedItems));

    // Create custom drag ghost if multiple items
    if (draggedItems.length > 1) {
        const ghost = createDragGhost(draggedItems.length);
        document.body.appendChild(ghost);
        event.dataTransfer.setDragImage(ghost, 0, 0);
        setTimeout(() => ghost.remove(), 0);
    }
}

/**
 * Handle drag over
 */
function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
}

/**
 * Handle drag enter
 */
function handleDragEnter(event) {
    const target = event.target.closest('.folder-card, .folder-tree-item');
    if (target && target !== draggedElement) {
        target.classList.add('drag-over');
    }
}

/**
 * Handle drag leave
 */
function handleDragLeave(event) {
    const target = event.target.closest('.folder-card, .folder-tree-item');
    if (target) {
        target.classList.remove('drag-over');
    }
}

/**
 * Handle drop
 */
async function handleDrop(event, targetFolderId) {
    event.preventDefault();
    event.stopPropagation();

    // Remove drag over class
    document.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over');
    });

    if (!draggedItems || draggedItems.length === 0) return;

    // Don't drop on self
    if (draggedItems.length === 1 && draggedItems[0].id === targetFolderId) {
        return;
    }

    // Prepare items for bulk move
    const documentIds = draggedItems
        .filter(item => item.type === 'document')
        .map(item => item.id);

    const folderIds = draggedItems
        .filter(item => item.type === 'folder')
        .map(item => item.id);

    // Perform bulk move
    await performBulkMove(documentIds, folderIds, targetFolderId);
}

/**
 * Handle drag end
 */
function handleDragEnd(event) {
    if (draggedElement) {
        draggedElement.classList.remove('dragging');
    }

    // Remove all drag-over classes
    document.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over');
    });

    draggedItems = [];
    draggedElement = null;
}

/**
 * Create custom drag ghost
 */
function createDragGhost(count) {
    const ghost = document.createElement('div');
    ghost.style.cssText = `
        position: absolute;
        top: -1000px;
        background: white;
        border: 2px solid #4285f4;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 500;
        color: #202124;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    ghost.textContent = `${count} items`;
    return ghost;
}

/**
 * Perform bulk move via API
 */
async function performBulkMove(documentIds, folderIds, targetFolderId) {
    if (documentIds.length === 0 && folderIds.length === 0) return;

    try {
        showLoading();

        const response = await fetch('/api/v1/documents/documents/bulk_move/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                document_ids: documentIds,
                folder_ids: folderIds,
                target_folder_id: targetFolderId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to move items');
        }

        const result = await response.json();

        showToast(`Moved ${result.moved_documents + result.moved_folders} item(s) successfully!`, 'success');

        // Clear selection
        clearSelection();

        // Refresh page
        setTimeout(() => window.location.reload(), 500);

    } catch (error) {
        console.error('Error moving items:', error);
        showToast('Error: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

/**
 * Mobile touch drag support
 */
let touchDragState = {
    active: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    element: null,
    ghost: null
};

function initTouchDrag() {
    document.querySelectorAll('.folder-card, .file-card').forEach(card => {
        let longPressTimer;

        card.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            touchDragState.startX = touch.clientX;
            touchDragState.startY = touch.clientY;
            touchDragState.element = card;

            // Long press to start drag
            longPressTimer = setTimeout(() => {
                if (navigator.vibrate) navigator.vibrate(50);
                startTouchDrag(card, touch.clientX, touch.clientY);
            }, 500);
        });

        card.addEventListener('touchmove', (e) => {
            clearTimeout(longPressTimer);

            if (touchDragState.active) {
                e.preventDefault();
                const touch = e.touches[0];
                updateTouchDragPosition(touch.clientX, touch.clientY);
                highlightDropTarget(touch.clientX, touch.clientY);
            }
        });

        card.addEventListener('touchend', (e) => {
            clearTimeout(longPressTimer);

            if (touchDragState.active) {
                const touch = e.changedTouches[0];
                performTouchDrop(touch.clientX, touch.clientY);
            }
        });
    });
}

function startTouchDrag(element, x, y) {
    touchDragState.active = true;
    touchDragState.currentX = x;
    touchDragState.currentY = y;

    // Create ghost
    const ghost = element.cloneNode(true);
    ghost.style.cssText = `
        position: fixed;
        left: ${x}px;
        top: ${y}px;
        opacity: 0.7;
        pointer-events: none;
        z-index: 9999;
    `;
    document.body.appendChild(ghost);
    touchDragState.ghost = ghost;

    element.style.opacity = '0.3';
}

function updateTouchDragPosition(x, y) {
    touchDragState.currentX = x;
    touchDragState.currentY = y;

    if (touchDragState.ghost) {
        touchDragState.ghost.style.left = x + 'px';
        touchDragState.ghost.style.top = y + 'px';
    }
}

function highlightDropTarget(x, y) {
    const element = document.elementFromPoint(x, y);
    const folder = element?.closest('.folder-card, .folder-tree-item');

    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));

    if (folder && folder !== touchDragState.element) {
        folder.classList.add('drag-over');
    }
}

function performTouchDrop(x, y) {
    const element = document.elementFromPoint(x, y);
    const folder = element?.closest('.folder-card, .folder-tree-item');

    // Remove ghost
    if (touchDragState.ghost) {
        touchDragState.ghost.remove();
    }

    // Restore opacity
    if (touchDragState.element) {
        touchDragState.element.style.opacity = '';
    }

    // Remove drag-over
    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));

    // Perform drop
    if (folder && folder !== touchDragState.element) {
        const targetFolderId = folder.dataset.folderId;
        const itemId = touchDragState.element.dataset.itemId;
        const itemType = touchDragState.element.dataset.itemType;

        handleDrop({ preventDefault: () => {}, stopPropagation: () => {} }, targetFolderId);
    }

    // Reset state
    touchDragState = {
        active: false,
        startX: 0,
        startY: 0,
        currentX: 0,
        currentY: 0,
        element: null,
        ghost: null
    };
}

// Initialize touch drag on load
document.addEventListener('DOMContentLoaded', initTouchDrag);
