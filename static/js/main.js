// Modern Notes & Todos - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all modules
    initializeMobileMenu();
    initializeTinyMCE();
    initializeClipboard();
    initializeNoteCards();
    initializeAlerts();
    initializeKeyboardShortcuts();
    initializeFormEnhancements();
    initializeTodoInteractions();
});

// ===== Mobile Menu =====
function initializeMobileMenu() {
    // On mobile (<992px), sidebar is hidden via CSS
    // Navbar toggler handles the Bootstrap collapse menu only
    // No additional sidebar functionality needed on mobile

    // Auto-close navbar menu when clicking a link
    const navbarCollapse = document.querySelector('.navbar-collapse');
    if (navbarCollapse && window.innerWidth < 992) {
        const navLinks = navbarCollapse.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                if (bsCollapse) {
                    bsCollapse.hide();
                }
            });
        });
    }
}

// ===== Note Cards =====
function initializeNoteCards() {
    const noteCards = document.querySelectorAll('.note-card[data-url]');

    noteCards.forEach(function(card) {
        // Click to navigate
        card.addEventListener('click', function(e) {
            // Don't navigate if clicking on a button or link inside the card
            if (e.target.closest('button, a, .btn')) return;
            window.location.href = this.dataset.url;
        });

        // Keyboard accessibility
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'link');

        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                window.location.href = this.dataset.url;
            }
        });
    });
}

// ===== Alert Auto-hide =====
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');

    alerts.forEach(function(alert) {
        // Add fade-in animation
        alert.style.animation = 'fadeIn 0.3s ease-out';

        // Auto-hide after 5 seconds
        setTimeout(function() {
            alert.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(function() {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 300);
        }, 5000);
    });
}

// ===== Keyboard Shortcuts =====
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ignore if typing in an input
        if (e.target.matches('input, textarea, [contenteditable]')) return;

        // Ctrl/Cmd + K: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        // N: New note (when not in input)
        if (e.key === 'n' && !e.ctrlKey && !e.metaKey) {
            const newNoteLink = document.querySelector('a[href*="note/create"]');
            if (newNoteLink) {
                e.preventDefault();
                window.location.href = newNoteLink.href;
            }
        }

        // Escape: Close modals/dropdowns
        if (e.key === 'Escape') {
            const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
            openDropdowns.forEach(d => d.classList.remove('show'));
        }
    });
}

// ===== Form Enhancements =====
function initializeFormEnhancements() {
    // Auto-save for note editing
    const noteForm = document.querySelector('#note-form');
    if (noteForm) {
        let saveTimeout;
        const noteId = noteForm.dataset.noteId;

        if (noteId) {
            noteForm.addEventListener('input', function() {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(function() {
                    autoSaveNote();
                }, 2000);
            });
        }
    }

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.btn-delete, [data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = this.dataset.confirm || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Form validation visual feedback
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        const inputs = form.querySelectorAll('input, textarea, select');

        inputs.forEach(function(input) {
            input.addEventListener('blur', function() {
                if (this.required && !this.value.trim()) {
                    this.classList.add('is-invalid');
                } else {
                    this.classList.remove('is-invalid');
                }
            });

            input.addEventListener('input', function() {
                this.classList.remove('is-invalid');
            });
        });
    });
}

// ===== Todo Interactions =====
function initializeTodoInteractions() {
    // Toggle todo completion via AJAX
    const todoCheckboxes = document.querySelectorAll('.todo-checkbox-input[data-toggle-url]');

    todoCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            const url = this.dataset.toggleUrl;
            const todoCard = this.closest('.todo-card');

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (todoCard) {
                        todoCard.classList.toggle('completed', data.is_completed);
                    }
                    showToast(data.message || 'Todo updated', 'success');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Failed to update todo', 'error');
                // Revert checkbox state
                this.checked = !this.checked;
            });
        });
    });
}

// ===== Auto-save Note =====
function autoSaveNote() {
    const form = document.querySelector('#note-form');
    if (!form) return;

    const formData = new FormData(form);
    const noteId = form.dataset.noteId;

    if (!noteId) return;

    showSavingIndicator();

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSavedIndicator();
        } else {
            showSaveError();
        }
    })
    .catch(error => {
        console.error('Auto-save error:', error);
        showSaveError();
    });
}

// ===== UI Feedback =====
function showSavingIndicator() {
    const indicator = document.getElementById('save-indicator');
    if (indicator) {
        indicator.innerHTML = '<i class="material-icons" style="font-size: 14px;">sync</i> Saving...';
        indicator.className = 'save-indicator saving';
    }
}

function showSavedIndicator() {
    const indicator = document.getElementById('save-indicator');
    if (indicator) {
        indicator.innerHTML = '<i class="material-icons" style="font-size: 14px;">check</i> Saved';
        indicator.className = 'save-indicator saved';
        setTimeout(function() {
            indicator.innerHTML = '';
            indicator.className = 'save-indicator';
        }, 2000);
    }
}

function showSaveError() {
    const indicator = document.getElementById('save-indicator');
    if (indicator) {
        indicator.innerHTML = '<i class="material-icons" style="font-size: 14px;">error_outline</i> Save failed';
        indicator.className = 'save-indicator error';
        setTimeout(function() {
            indicator.innerHTML = '';
            indicator.className = 'save-indicator';
        }, 3000);
    }
}

// ===== Toast Notifications =====
function showToast(message, type = 'info') {
    const container = getToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="material-icons">${getToastIcon(type)}</i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function getToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 8px;
        `;
        document.body.appendChild(container);
    }
    return container;
}

function getToastIcon(type) {
    const icons = {
        success: 'check_circle',
        error: 'error',
        warning: 'warning',
        info: 'info'
    };
    return icons[type] || 'info';
}

// ===== Utility Functions =====
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

// ===== CSRF Token Setup =====
const csrftoken = getCookie('csrftoken');
if (csrftoken) {
    document.addEventListener('DOMContentLoaded', function() {
        const forms = document.querySelectorAll('form');
        forms.forEach(function(form) {
            if (!form.querySelector('[name="csrfmiddlewaretoken"]')) {
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = csrftoken;
                form.appendChild(csrfInput);
            }
        });
    });
}

// ===== TinyMCE Initialization =====
function initializeTinyMCE() {
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '.tinymce-editor',
            height: 400,
            width: '100%',
            cleanup_on_startup: true,
            custom_undo_redo_levels: 20,
            theme: 'silver',
            skin: 'oxide',
            plugins: [
                'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview', 'anchor',
                'searchreplace', 'visualblocks', 'code', 'fullscreen',
                'insertdatetime', 'media', 'table', 'help', 'wordcount'
            ],
            toolbar: 'undo redo | blocks | bold italic forecolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | help',
            menubar: false,
            statusbar: true,
            resize: true,
            branding: false,
            content_style: `
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    font-size: 14px;
                    line-height: 1.6;
                    color: #0f172a;
                    padding: 16px;
                }
                p { margin: 0 0 1em; }
                h1, h2, h3 { margin: 1.5em 0 0.5em; font-weight: 600; }
            `,
            setup: function(editor) {
                editor.on('change', function() {
                    editor.save();
                });
            }
        });
    }
}

// ===== Clipboard Functionality =====
function initializeClipboard() {
    const copyButtons = document.querySelectorAll('.copy-to-clipboard');
    copyButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const textToCopy = this.getAttribute('data-copy-text');
            if (textToCopy) {
                copyToClipboard(textToCopy, this);
            }
        });
    });
}

function copyToClipboard(text, buttonElement) {
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text)
            .then(() => showCopySuccess(buttonElement))
            .catch(() => fallbackCopy(text, buttonElement));
    } else {
        fallbackCopy(text, buttonElement);
    }
}

function fallbackCopy(text, buttonElement) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.cssText = 'position: fixed; left: -9999px;';
    document.body.appendChild(textarea);

    try {
        textarea.select();
        document.execCommand('copy');
        showCopySuccess(buttonElement);
    } catch (err) {
        showCopyError(buttonElement);
    } finally {
        document.body.removeChild(textarea);
    }
}

function showCopySuccess(buttonElement) {
    const originalHTML = buttonElement.innerHTML;
    buttonElement.innerHTML = '<i class="material-icons" style="font-size: 14px;">check</i> Copied!';
    buttonElement.classList.add('btn-success');

    setTimeout(() => {
        buttonElement.innerHTML = originalHTML;
        buttonElement.classList.remove('btn-success');
    }, 2000);
}

function showCopyError(buttonElement) {
    const originalHTML = buttonElement.innerHTML;
    buttonElement.innerHTML = '<i class="material-icons" style="font-size: 14px;">error</i> Failed';
    buttonElement.classList.add('btn-danger');

    setTimeout(() => {
        buttonElement.innerHTML = originalHTML;
        buttonElement.classList.remove('btn-danger');
    }, 2000);
}

// ===== CSS for Toast Notifications =====
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 16px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        font-size: 14px;
        transform: translateX(120%);
        transition: transform 0.3s ease;
    }

    .toast.show {
        transform: translateX(0);
    }

    .toast i {
        font-size: 18px;
    }

    .toast-success { border-left: 3px solid #10b981; }
    .toast-success i { color: #10b981; }

    .toast-error { border-left: 3px solid #ef4444; }
    .toast-error i { color: #ef4444; }

    .toast-warning { border-left: 3px solid #f59e0b; }
    .toast-warning i { color: #f59e0b; }

    .toast-info { border-left: 3px solid #3b82f6; }
    .toast-info i { color: #3b82f6; }

    .save-indicator {
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    .save-indicator.saving { color: #64748b; }
    .save-indicator.saved { color: #10b981; }
    .save-indicator.error { color: #ef4444; }

    @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-8px); }
    }
`;
document.head.appendChild(toastStyles);
