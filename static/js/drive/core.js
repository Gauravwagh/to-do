/**
 * Core Drive Functionality
 * Main functions for navigation, view switching, and utilities
 */

// Global state
const driveState = {
    currentFolder: null,
    selectedItems: new Set(),
    view: 'grid'
};

/**
 * Navigation
 */
function navigateToFolder(folderId, event) {
    if (event) {
        event.stopPropagation();
    }

    if (folderId) {
        window.location.href = `/documents/drive/folder/${folderId}/`;
    } else {
        window.location.href = '/documents/drive/';
    }
}

/**
 * Handle item click (single-click to open)
 * Prevents navigation when clicking checkbox or other controls
 */
function handleItemClick(event, itemType, itemId) {
    // Don't navigate if clicking checkbox or its container
    if (event.target.type === 'checkbox' ||
        event.target.closest('.item-checkbox') ||
        event.target.closest('.item-actions')) {
        return;
    }

    // Navigate to the item
    if (itemType === 'folder') {
        navigateToFolder(itemId, event);
    } else if (itemType === 'document') {
        window.location.href = `/documents/${itemId}/`;
    }
}

/**
 * Sidebar Toggle (Mobile)
 */
function toggleSidebar() {
    const sidebar = document.getElementById('driveSidebar');
    const overlay = document.getElementById('sidebarOverlay');

    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
}

function closeSidebar() {
    const sidebar = document.getElementById('driveSidebar');
    const overlay = document.getElementById('sidebarOverlay');

    sidebar.classList.remove('open');
    overlay.classList.remove('active');
}

/**
 * View Toggle (Grid/List)
 */
function setView(view) {
    const grids = document.querySelectorAll('.items-grid');
    const gridBtn = document.getElementById('gridViewBtn');
    const listBtn = document.getElementById('listViewBtn');

    if (view === 'list') {
        grids.forEach(g => {
            g.style.gridTemplateColumns = '1fr';
            g.querySelectorAll('.file-card').forEach(c => {
                const iconWrapper = c.querySelector('.file-icon-wrapper');
                if (iconWrapper) {
                    iconWrapper.style.height = '40px';
                    iconWrapper.style.width = '40px';
                    iconWrapper.querySelector('i').style.fontSize = '24px';
                }
            });
        });
        listBtn.classList.add('active');
        listBtn.classList.remove('btn-outline-secondary');
        listBtn.classList.add('btn-secondary');
        gridBtn.classList.remove('active');
        gridBtn.classList.remove('btn-secondary');
        gridBtn.classList.add('btn-outline-secondary');
    } else {
        grids.forEach(g => {
            g.style.gridTemplateColumns = 'repeat(auto-fill, minmax(180px, 1fr))';
            g.querySelectorAll('.file-card').forEach(c => {
                const iconWrapper = c.querySelector('.file-icon-wrapper');
                if (iconWrapper) {
                    iconWrapper.style.height = '100px';
                    iconWrapper.style.width = '100%';
                    iconWrapper.querySelector('i').style.fontSize = '40px';
                }
            });
        });
        gridBtn.classList.add('active');
        gridBtn.classList.remove('btn-outline-secondary');
        gridBtn.classList.add('btn-secondary');
        listBtn.classList.remove('active');
        listBtn.classList.remove('btn-secondary');
        listBtn.classList.add('btn-outline-secondary');
    }

    driveState.view = view;
    localStorage.setItem('driveView', view);
}

/**
 * Keyboard Shortcuts
 */
function handleKeyboardShortcuts(event) {
    // Ctrl+A or Cmd+A - Select all
    if ((event.ctrlKey || event.metaKey) && event.key === 'a') {
        event.preventDefault();
        selectAll();
    }

    // Escape - Clear selection or close modals
    if (event.key === 'Escape') {
        clearSelection();
        document.getElementById('contextMenu').style.display = 'none';
    }

    // Delete - Delete selected items
    if (event.key === 'Delete' && driveState.selectedItems.size > 0) {
        event.preventDefault();
        bulkDelete();
    }
}

/**
 * API Utilities
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCsrfToken() {
    return getCookie('csrftoken');
}

async function apiCall(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.error || 'Request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showToast('Error: ' + error.message, 'danger');
        throw error;
    }
}

/**
 * Toast Notifications
 */
function showToast(message, type = 'success') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 350px;';
        document.body.appendChild(toastContainer);
    }

    // Create toast
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.style.cssText = 'margin-bottom: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    toastContainer.appendChild(toast);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
    }, 5000);
}

/**
 * Loading Spinner
 */
function showLoading() {
    const spinner = document.createElement('div');
    spinner.id = 'loadingSpinner';
    spinner.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 9999;';
    spinner.innerHTML = `
        <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    document.body.appendChild(spinner);
}

function hideLoading() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.remove();
    }
}

/**
 * Confirmation Dialog
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Get current folder ID from URL
 */
function getCurrentFolderId() {
    const pathParts = window.location.pathname.split('/');
    const folderIndex = pathParts.indexOf('folder');
    if (folderIndex !== -1 && pathParts[folderIndex + 1]) {
        return pathParts[folderIndex + 1].replace('/', '');
    }
    return null;
}

/**
 * Initialize
 */
document.addEventListener('DOMContentLoaded', () => {
    driveState.currentFolder = getCurrentFolderId();
});
