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
                action: `deleteFolder('${itemId}', contextMenuTarget.name)`,
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
 * Show new folder modal for creating folder inside
 */
function promptCreateFolderInside(parentId) {
    const modal = new bootstrap.Modal(document.getElementById('newFolderInsideModal'));
    const input = document.getElementById('newFolderNameInput');
    const parentIdInput = document.getElementById('newFolderParentId');

    input.value = '';
    parentIdInput.value = parentId;

    modal.show();

    // Focus input after modal is shown
    setTimeout(() => input.focus(), 300);
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
 * Show move dialog with improved UI
 */
async function showMoveDialog(itemType, itemId) {
    // Set values in move modal
    document.getElementById('moveItemType').value = itemType;
    document.getElementById('moveItemId').value = itemId;
    document.getElementById('moveItemName').textContent = contextMenuTarget.name;
    document.getElementById('moveTargetFolderId').value = '';

    // Load folder tree
    const treeContainer = document.getElementById('moveFolderTree');
    treeContainer.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm" role="status"></div></div>';

    try {
        const response = await fetch('/api/v1/documents/categories/tree/', {
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load folders');
        }

        const folders = await response.json();

        // Render folder tree with selection
        treeContainer.innerHTML = '';

        // Add "My Drive" (root) option
        const rootOption = document.createElement('div');
        rootOption.className = 'move-folder-option';
        rootOption.innerHTML = `
            <div class="d-flex align-items-center gap-2 p-2" style="cursor: pointer; border-radius: 4px;">
                <i class="material-icons">home</i>
                <span>My Drive</span>
            </div>
        `;
        rootOption.onclick = () => selectMoveTarget(rootOption, 'root');
        treeContainer.appendChild(rootOption);

        // Render folders recursively
        renderMoveFolderTree(folders, treeContainer, itemId, itemType);

    } catch (error) {
        console.error('Error loading folders:', error);
        treeContainer.innerHTML = '<div class="text-danger text-center py-3">Failed to load folders</div>';
    }

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('moveModal'));
    modal.show();
}

/**
 * Render folder tree for move dialog
 */
function renderMoveFolderTree(folders, container, excludeId, itemType, depth = 0) {
    folders.forEach(folder => {
        // Don't show the folder we're moving or its children
        if (folder.id === excludeId) {
            return;
        }

        const folderOption = document.createElement('div');
        folderOption.className = 'move-folder-option';
        folderOption.style.paddingLeft = `${depth * 20}px`;
        folderOption.innerHTML = `
            <div class="d-flex align-items-center gap-2 p-2" style="cursor: pointer; border-radius: 4px;">
                <i class="material-icons" style="color: ${folder.color || '#fbbf24'};">folder</i>
                <span>${folder.name}</span>
            </div>
        `;
        folderOption.onclick = () => selectMoveTarget(folderOption, folder.id);
        container.appendChild(folderOption);

        // Render children
        if (folder.children && folder.children.length > 0) {
            renderMoveFolderTree(folder.children, container, excludeId, itemType, depth + 1);
        }
    });
}

/**
 * Select target folder for move
 */
function selectMoveTarget(element, folderId) {
    // Remove previous selection
    document.querySelectorAll('.move-folder-option').forEach(el => {
        el.querySelector('div').style.background = '';
    });

    // Highlight selected
    element.querySelector('div').style.background = '#e8f0fe';

    // Store selection
    document.getElementById('moveTargetFolderId').value = folderId;
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
 * Delete document with custom modal confirmation
 */
async function deleteDocument(documentId) {
    showDeleteConfirmation('Are you sure you want to delete 1 item(s)?', async () => {
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
    });
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

    // Event listener for "Create Folder" button in new folder modal
    const createFolderBtn = document.getElementById('createFolderBtn');
    if (createFolderBtn) {
        createFolderBtn.addEventListener('click', () => {
            const input = document.getElementById('newFolderNameInput');
            const parentId = document.getElementById('newFolderParentId').value;
            const name = input.value.trim();

            if (name) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('newFolderInsideModal'));
                modal.hide();
                createFolder(name, parentId || null);
            }
        });
    }

    // Allow Enter key to submit in new folder modal
    const newFolderInput = document.getElementById('newFolderNameInput');
    if (newFolderInput) {
        newFolderInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('createFolderBtn').click();
            }
        });
    }

    // Event listener for "Move" button in move modal
    const confirmMoveBtn = document.getElementById('confirmMoveBtn');
    if (confirmMoveBtn) {
        confirmMoveBtn.addEventListener('click', async () => {
            const itemType = document.getElementById('moveItemType').value;
            const itemId = document.getElementById('moveItemId').value;
            const targetFolderId = document.getElementById('moveTargetFolderId').value;

            if (!targetFolderId) {
                showToast('Please select a destination folder', 'warning');
                return;
            }

            const modal = bootstrap.Modal.getInstance(document.getElementById('moveModal'));
            modal.hide();

            try {
                showLoading();

                const url = itemType === 'folder'
                    ? `/api/v1/documents/categories/${itemId}/move/`
                    : `/api/v1/documents/documents/${itemId}/`;

                const method = itemType === 'folder' ? 'POST' : 'PATCH';
                const body = itemType === 'folder'
                    ? { parent: targetFolderId === 'root' ? null : targetFolderId }
                    : { category: targetFolderId === 'root' ? null : targetFolderId };

                const response = await fetch(url, {
                    method: method,
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify(body)
                });

                if (!response.ok) {
                    throw new Error('Failed to move item');
                }

                showToast('Item moved successfully!', 'success');
                setTimeout(() => window.location.reload(), 500);

            } catch (error) {
                console.error('Error moving item:', error);
                showToast('Error: ' + error.message, 'danger');
            } finally {
                hideLoading();
            }
        });
    }
});
