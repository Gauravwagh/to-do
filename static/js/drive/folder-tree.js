/**
 * Folder Tree Component
 * Loads and renders the hierarchical folder tree in the sidebar
 */

let folderTreeData = [];
let expandedFolders = new Set();

/**
 * Load folder tree from API
 */
async function loadFolderTree() {
    const container = document.getElementById('folderTreeContainer');

    try {
        const response = await fetch('/api/v1/documents/categories/tree/', {
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load folder tree');
        }

        folderTreeData = await response.json();

        // Load expanded state from localStorage
        const savedExpanded = localStorage.getItem('expandedFolders');
        if (savedExpanded) {
            expandedFolders = new Set(JSON.parse(savedExpanded));
        }

        // Render tree
        renderFolderTree(folderTreeData, container);

    } catch (error) {
        console.error('Error loading folder tree:', error);
        container.innerHTML = `
            <div class="text-center text-danger py-3">
                <small>Failed to load folders</small>
            </div>
        `;
    }
}

/**
 * Render folder tree recursively
 */
function renderFolderTree(folders, container, depth = 0) {
    if (!folders || folders.length === 0) {
        if (depth === 0) {
            container.innerHTML = '<div class="text-center text-muted py-3"><small>No folders yet</small></div>';
        }
        return;
    }

    if (depth === 0) {
        container.innerHTML = '';
    }

    folders.forEach(folder => {
        const hasChildren = folder.children && folder.children.length > 0;
        const isExpanded = expandedFolders.has(folder.id);
        const isActive = getCurrentFolderId() === folder.id;

        // Create folder item
        const folderItem = document.createElement('div');
        folderItem.className = `folder-tree-item ${isActive ? 'active' : ''}`;
        folderItem.dataset.folderId = folder.id;
        folderItem.style.paddingLeft = `${16 + depth * 20}px`;

        // Toggle button
        const toggle = document.createElement('span');
        toggle.className = `folder-toggle ${isExpanded ? 'expanded' : ''}`;
        if (hasChildren) {
            toggle.innerHTML = '<i class="material-icons">chevron_right</i>';
            toggle.onclick = (e) => {
                e.stopPropagation();
                toggleFolder(folder.id);
            };
        }
        folderItem.appendChild(toggle);

        // Folder icon
        const icon = document.createElement('i');
        icon.className = 'material-icons folder-icon';
        icon.style.color = folder.color || '#fbbf24';
        icon.textContent = 'folder';
        folderItem.appendChild(icon);

        // Folder name
        const name = document.createElement('span');
        name.className = 'folder-name';
        name.textContent = folder.name;
        name.title = folder.path;
        folderItem.appendChild(name);

        // Document count
        if (folder.document_count > 0) {
            const count = document.createElement('span');
            count.className = 'folder-count';
            count.textContent = folder.document_count;
            folderItem.appendChild(count);
        }

        // Click to navigate
        folderItem.onclick = (e) => {
            if (!e.target.classList.contains('folder-toggle') && !e.target.closest('.folder-toggle')) {
                navigateToFolder(folder.id, e);
            }
        };

        // Add context menu
        folderItem.oncontextmenu = (e) => {
            e.preventDefault();
            showContextMenu(e, 'folder', folder.id, folder.name);
        };

        // Make draggable
        folderItem.draggable = true;
        folderItem.ondragstart = (e) => handleDragStart(e, folder.id, 'folder');

        // Make drop target
        folderItem.ondragover = (e) => handleDragOver(e);
        folderItem.ondragenter = (e) => handleDragEnter(e);
        folderItem.ondragleave = (e) => handleDragLeave(e);
        folderItem.ondrop = (e) => handleDrop(e, folder.id);

        container.appendChild(folderItem);

        // Render children if expanded
        if (hasChildren && isExpanded) {
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'folder-children expanded';
            childrenContainer.dataset.parentId = folder.id;
            container.appendChild(childrenContainer);

            renderFolderTree(folder.children, childrenContainer, depth + 1);
        } else if (hasChildren) {
            // Create placeholder for children
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'folder-children';
            childrenContainer.dataset.parentId = folder.id;
            container.appendChild(childrenContainer);
        }
    });
}

/**
 * Toggle folder expand/collapse
 */
function toggleFolder(folderId) {
    const isExpanded = expandedFolders.has(folderId);

    if (isExpanded) {
        expandedFolders.delete(folderId);
    } else {
        expandedFolders.add(folderId);
    }

    // Save to localStorage
    localStorage.setItem('expandedFolders', JSON.stringify([...expandedFolders]));

    // Find the folder item
    const folderItem = document.querySelector(`.folder-tree-item[data-folder-id="${folderId}"]`);
    if (!folderItem) return;

    const toggle = folderItem.querySelector('.folder-toggle');
    const childrenContainer = folderItem.nextElementSibling;

    if (toggle && childrenContainer && childrenContainer.classList.contains('folder-children')) {
        if (isExpanded) {
            // Collapse
            toggle.classList.remove('expanded');
            childrenContainer.classList.remove('expanded');
        } else {
            // Expand
            toggle.classList.add('expanded');
            childrenContainer.classList.add('expanded');

            // If children haven't been rendered yet, render them
            if (childrenContainer.children.length === 0) {
                const folder = findFolderById(folderTreeData, folderId);
                if (folder && folder.children) {
                    const depth = parseInt(folderItem.style.paddingLeft) / 20;
                    renderFolderTree(folder.children, childrenContainer, depth);
                }
            }
        }
    }
}

/**
 * Find folder by ID in tree
 */
function findFolderById(folders, id) {
    for (const folder of folders) {
        if (folder.id === id) {
            return folder;
        }
        if (folder.children) {
            const found = findFolderById(folder.children, id);
            if (found) return found;
        }
    }
    return null;
}

/**
 * Refresh folder tree
 */
async function refreshFolderTree() {
    await loadFolderTree();
}

/**
 * Expand to current folder (show path)
 */
function expandToCurrentFolder() {
    const currentFolderId = getCurrentFolderId();
    if (!currentFolderId) return;

    // Get folder from tree
    const folder = findFolderById(folderTreeData, currentFolderId);
    if (!folder) return;

    // Expand all ancestors
    const ancestors = getAncestorIds(folder);
    ancestors.forEach(id => {
        if (!expandedFolders.has(id)) {
            expandedFolders.add(id);
        }
    });

    // Save and re-render
    localStorage.setItem('expandedFolders', JSON.stringify([...expandedFolders]));
    renderFolderTree(folderTreeData, document.getElementById('folderTreeContainer'));
}

/**
 * Get ancestor folder IDs
 */
function getAncestorIds(folder) {
    const ancestors = [];
    let current = folder.parent;

    while (current) {
        ancestors.unshift(current);
        const parentFolder = findFolderById(folderTreeData, current);
        current = parentFolder ? parentFolder.parent : null;
    }

    return ancestors;
}

/**
 * Create new folder via API
 */
async function createFolder(name, parentId = null) {
    try {
        showLoading();

        const data = {
            name: name,
            parent: parentId
        };

        const response = await fetch('/api/v1/documents/categories/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.name ? error.name[0] : 'Failed to create folder');
        }

        const newFolder = await response.json();

        // Refresh tree
        await refreshFolderTree();

        // Expand parent if it exists
        if (parentId && !expandedFolders.has(parentId)) {
            toggleFolder(parentId);
        }

        showToast(`Folder "${name}" created successfully!`, 'success');

        return newFolder;

    } catch (error) {
        console.error('Error creating folder:', error);
        showToast('Error: ' + error.message, 'danger');
        throw error;
    } finally {
        hideLoading();
    }
}

/**
 * Rename folder via API
 */
async function renameFolder(folderId, newName) {
    try {
        showLoading();

        const response = await fetch(`/api/v1/documents/categories/${folderId}/`, {
            method: 'PATCH',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ name: newName })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.name ? error.name[0] : 'Failed to rename folder');
        }

        // Refresh tree
        await refreshFolderTree();

        showToast('Folder renamed successfully!', 'success');

    } catch (error) {
        console.error('Error renaming folder:', error);
        showToast('Error: ' + error.message, 'danger');
        throw error;
    } finally {
        hideLoading();
    }
}

/**
 * Delete folder via API
 */
async function deleteFolder(folderId, folderName) {
    if (!confirm(`Are you sure you want to delete "${folderName}" and all its contents?`)) {
        return;
    }

    try {
        showLoading();

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

        // Refresh tree
        await refreshFolderTree();

        // If we're in the deleted folder, navigate to root
        if (getCurrentFolderId() === folderId) {
            window.location.href = '/documents/drive/';
        } else {
            showToast(`Folder "${folderName}" deleted successfully!`, 'success');
        }

    } catch (error) {
        console.error('Error deleting folder:', error);
        showToast('Error: ' + error.message, 'danger');
        throw error;
    } finally {
        hideLoading();
    }
}
