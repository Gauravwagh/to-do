/**
 * Context Menu Component
 * Right-click menu for files and folders
 */

let contextMenuTarget = {
    type: null,
    id: null,
    name: null
};

/**
 * Show context menu
 */
function showContextMenu(event, itemType, itemId, itemName) {
    event.preventDefault();
    event.stopPropagation();

    const menu = document.getElementById('contextMenu');

    // Store target info
    contextMenuTarget = {
        type: itemType,
        id: itemId,
        name: itemName
    };

    // Build menu items based on type
    const menuItems = buildContextMenuItems(itemType, itemId);

    // Render menu
    menu.innerHTML = menuItems.map(item => {
        if (item === 'divider') {
            return '<div class="context-menu-divider"></div>';
        }
        return `
            <div class="context-menu-item ${item.danger ? 'danger' : ''}" onclick="${item.action}">
                <i class="material-icons" style="font-size: 18px;">${item.icon}</i>
                <span>${item.label}</span>
            </div>
        `;
    }).join('');

    // Position menu
    positionContextMenu(menu, event.clientX, event.clientY);

    // Show menu
    menu.style.display = 'block';

    // Hide menu on any click
    setTimeout(() => {
        document.addEventListener('click', hideContextMenu, { once: true });
    }, 10);
}

/**
 * Build context menu items based on type
 */
function buildContextMenuItems(itemType, itemId) {
    if (itemType === 'folder') {
        return [
            {
                icon: 'folder_open',
                label: 'Open',
                action: `navigateToFolder('${itemId}', event)`
            },
            {
                icon: 'edit',
                label: 'Rename',
                action: `promptRenameFolder('${itemId}')`
            },
            {
                icon: 'drive_file_move',
                label: 'Move',
                action: `showMoveDialog('folder', '${itemId}')`
            },
            {
                icon: 'create_new_folder',
                label: 'New folder inside',
                action: `promptCreateFolderInside('${itemId}')`
            },
            'divider',
            {
                icon: 'delete',
                label: 'Delete',
                action: `deleteFolder('${itemId}', '${contextMenuTarget.name}')`,
                danger: true
            }
        ];
    } else if (itemType === 'document') {
        return [
            {
                icon: 'visibility',
                label: 'View',
                action: `window.location='/documents/doc/${itemId}/'`
            },
            {
                icon: 'download',
                label: 'Download',
                action: `window.location='/documents/doc/${itemId}/download/'`
            },
            {
                icon: 'drive_file_move',
                label: 'Move',
                action: `showMoveDialog('document', '${itemId}')`
            },
            {
                icon: 'star_border',
                label: 'Star',
                action: `toggleStar('${itemId}')`
            },
            {
                icon: 'share',
                label: 'Share',
                action: `showShareDialog('${itemId}')`
            },
            'divider',
            {
                icon: 'delete',
                label: 'Delete',
                action: `deleteDocument('${itemId}')`,
                danger: true
            }
        ];
    } else if (itemType === 'background') {
        return [
            {
                icon: 'create_new_folder',
                label: 'New Folder',
                action: `showNewFolderModal()`
            },
            {
                icon: 'upload_file',
                label: 'Upload Files',
                action: `showUploadModal()`
            },
            'divider',
            {
                icon: 'refresh',
                label: 'Refresh',
                action: `window.location.reload()`
            }
        ];
    }

    return [];
}

/**
 * Position context menu at cursor
 */
function positionContextMenu(menu, x, y) {
    // Get menu dimensions
    menu.style.left = '0px';
    menu.style.top = '0px';
    menu.style.display = 'block';

    const menuWidth = menu.offsetWidth;
    const menuHeight = menu.offsetHeight;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    // Adjust position if near edges
    let left = x;
    let top = y;

    if (x + menuWidth > windowWidth) {
        left = windowWidth - menuWidth - 10;
    }

    if (y + menuHeight > windowHeight) {
        top = windowHeight - menuHeight - 10;
    }

    menu.style.left = left + 'px';
    menu.style.top = top + 'px';
}

/**
 * Hide context menu
 */
function hideContextMenu() {
    const menu = document.getElementById('contextMenu');
    menu.style.display = 'none';
    contextMenuTarget = { type: null, id: null, name: null };
}

/**
 * Prompt rename folder
 */
function promptRenameFolder(folderId) {
    const newName = prompt('Enter new folder name:', contextMenuTarget.name);
    if (newName && newName.trim() && newName !== contextMenuTarget.name) {
        renameFolder(folderId, newName.trim());
    }
}

/**
 * Prompt create folder inside
 */
function promptCreateFolderInside(parentId) {
    const name = prompt('Enter folder name:');
    if (name && name.trim()) {
        createFolder(name.trim(), parentId);
    }
}

/**
 * Show new folder modal
 */
function showNewFolderModal() {
    const modal = new bootstrap.Modal(document.getElementById('newFolderModal'));
    modal.show();
}

/**
 * Show upload modal
 */
function showUploadModal() {
    const modal = new bootstrap.Modal(document.getElementById('uploadModal'));
    modal.show();
}

/**
 * Show move dialog
 */
function showMoveDialog(itemType, itemId) {
    // Set values in move modal
    document.getElementById('moveItemType').value = itemType;
    document.getElementById('moveItemId').value = itemId;
    document.getElementById('moveItemName').textContent = contextMenuTarget.name;

    // Clear previous selection
    document.querySelectorAll('.folder-tree-item').forEach(el => {
        el.classList.remove('selected');
    });

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('moveModal'));
    modal.show();
}

/**
 * Show share dialog
 */
function showShareDialog(documentId) {
    // Set document ID in share modal
    document.getElementById('shareDocumentId').value = documentId;

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('shareModal'));
    modal.show();
}

/**
 * Toggle star on document
 */
async function toggleStar(documentId) {
    try {
        const response = await fetch(`/api/v1/documents/documents/${documentId}/toggle_favorite/`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to toggle star');
        }

        // Refresh page
        window.location.reload();

    } catch (error) {
        console.error('Error toggling star:', error);
        showToast('Error: ' + error.message, 'danger');
    }
}

/**
 * Delete document
 */
async function deleteDocument(documentId) {
    if (!confirm(`Are you sure you want to delete "${contextMenuTarget.name}"?`)) {
        return;
    }

    try {
        showLoading();

        const response = await fetch(`/api/v1/documents/documents/${documentId}/`, {
            method: 'DELETE',
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to delete document');
        }

        showToast('Document deleted successfully!', 'success');

        // Refresh page after short delay
        setTimeout(() => window.location.reload(), 500);

    } catch (error) {
        console.error('Error deleting document:', error);
        showToast('Error: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

/**
 * Background context menu (right-click on empty space)
 */
document.addEventListener('DOMContentLoaded', () => {
    const driveContent = document.querySelector('.drive-content');
    if (driveContent) {
        driveContent.addEventListener('contextmenu', (event) => {
            // Only show if clicking on empty space (not on cards)
            if (event.target === driveContent || event.target.closest('.empty-state')) {
                showContextMenu(event, 'background', null, null);
            }
        });
    }
});

/**
 * Mobile long-press support
 */
let longPressTimer = null;
let longPressTarget = null;

function setupLongPress(element, itemType, itemId, itemName) {
    element.addEventListener('touchstart', (e) => {
        longPressTarget = { type: itemType, id: itemId, name: itemName };
        longPressTimer = setTimeout(() => {
            // Vibrate if supported
            if (navigator.vibrate) {
                navigator.vibrate(50);
            }

            // Show context menu
            const touch = e.touches[0];
            showContextMenu({
                preventDefault: () => {},
                stopPropagation: () => {},
                clientX: touch.clientX,
                clientY: touch.clientY
            }, itemType, itemId, itemName);
        }, 500);
    });

    element.addEventListener('touchend', () => {
        clearTimeout(longPressTimer);
        longPressTarget = null;
    });

    element.addEventListener('touchmove', () => {
        clearTimeout(longPressTimer);
        longPressTarget = null;
    });
}

// Apply long-press to all cards
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.folder-card, .file-card').forEach(card => {
        const itemType = card.dataset.itemType;
        const itemId = card.dataset.itemId;
        const itemName = card.querySelector('.folder-name, .file-name').textContent;

        setupLongPress(card, itemType, itemId, itemName);
    });
});
