// Main JavaScript for Evernote Clone

document.addEventListener('DOMContentLoaded', function() {
    // Initialize TinyMCE
    initializeTinyMCE();
    
    // Initialize clipboard functionality
    initializeClipboard();
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.querySelector('.btn-close')) {
                alert.querySelector('.btn-close').click();
            }
        });
    }, 5000);

    // Note card click handlers
    const noteCards = document.querySelectorAll('.note-card[data-url]');
    noteCards.forEach(function(card) {
        card.addEventListener('click', function() {
            window.location.href = this.dataset.url;
        });
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // Auto-save for note editing (if on note edit page)
    const noteContentField = document.getElementById('id_content');
    if (noteContentField) {
        let saveTimeout;
        noteContentField.addEventListener('input', function() {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(function() {
                autoSaveNote();
            }, 2000); // Auto-save after 2 seconds of inactivity
        });
    }

    // Search functionality
    const searchForm = document.querySelector('form[action*="search"]');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.addEventListener('keyup', function(e) {
                if (e.key === 'Enter') {
                    searchForm.submit();
                }
            });
        }
    }
});

// Auto-save function for notes
function autoSaveNote() {
    const form = document.querySelector('#note-form');
    if (!form) return;

    const formData = new FormData(form);
    const noteId = form.dataset.noteId;
    
    if (!noteId) return; // Don't auto-save new notes

    // Show saving indicator
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

// UI feedback functions
function showSavingIndicator() {
    const indicator = document.getElementById('save-indicator');
    if (indicator) {
        indicator.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        indicator.className = 'text-muted';
    }
}

function showSavedIndicator() {
    const indicator = document.getElementById('save-indicator');
    if (indicator) {
        indicator.innerHTML = '<i class="fas fa-check"></i> Saved';
        indicator.className = 'text-success';
        setTimeout(function() {
            indicator.innerHTML = '';
        }, 2000);
    }
}

function showSaveError() {
    const indicator = document.getElementById('save-indicator');
    if (indicator) {
        indicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Save failed';
        indicator.className = 'text-danger';
        setTimeout(function() {
            indicator.innerHTML = '';
        }, 3000);
    }
}

// Utility functions
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

// Set up CSRF token for AJAX requests
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

// TinyMCE initialization
function initializeTinyMCE() {
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '.tinymce-editor',
            height: 400,
            width: '100%',
            cleanup_on_startup: true,
            custom_undo_redo_levels: 20,
            theme: 'silver',
            plugins: [
                'advlist autolink lists link image charmap print preview anchor',
                'searchreplace visualblocks code fullscreen',
                'insertdatetime media table contextmenu paste code'
            ],
            toolbar: 'undo redo | formatselect | bold italic backcolor | \
                alignleft aligncenter alignright alignjustify | \
                bullist numlist outdent indent | removeformat | help',
            menubar: false,
            statusbar: true,
            resize: true,
            branding: false,
            content_css: '/static/css/style.css',
            api_key: '70r2h4ki9m7s4vx8qw2lv8w1cz4izt726m4trl79l5i6bbks',
            setup: function(editor) {
                editor.on('change', function() {
                    editor.save();
                });
            }
        });
    }
}

// Clipboard functionality
function copyToClipboard(text, buttonElement) {
    // Create a temporary textarea element
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-999999px';
    textarea.style.top = '-999999px';
    document.body.appendChild(textarea);
    
    try {
        // Select and copy the text
        textarea.select();
        textarea.setSelectionRange(0, 99999); // For mobile devices
        
        const successful = document.execCommand('copy');
        
        if (successful) {
            showCopySuccess(buttonElement);
        } else {
            // Fallback for modern browsers
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(() => {
                    showCopySuccess(buttonElement);
                }).catch(() => {
                    showCopyError(buttonElement);
                });
            } else {
                showCopyError(buttonElement);
            }
        }
    } catch (err) {
        console.error('Failed to copy text: ', err);
        showCopyError(buttonElement);
    } finally {
        // Clean up
        document.body.removeChild(textarea);
    }
}

function showCopySuccess(buttonElement) {
    const originalText = buttonElement.innerHTML;
    const originalClass = buttonElement.className;
    
    buttonElement.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
    buttonElement.className = originalClass.replace('btn-outline-secondary', 'btn-success');
    
    setTimeout(() => {
        buttonElement.innerHTML = originalText;
        buttonElement.className = originalClass;
    }, 2000);
}

function showCopyError(buttonElement) {
    const originalText = buttonElement.innerHTML;
    const originalClass = buttonElement.className;
    
    buttonElement.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Failed';
    buttonElement.className = originalClass.replace('btn-outline-secondary', 'btn-danger');
    
    setTimeout(() => {
        buttonElement.innerHTML = originalText;
        buttonElement.className = originalClass;
    }, 2000);
}

// Initialize clipboard functionality
function initializeClipboard() {
    // Add copy to clipboard functionality to copy buttons
    const copyButtons = document.querySelectorAll('.copy-to-clipboard');
    copyButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Get the text to copy from data attribute or find it in the page
            const textToCopy = this.getAttribute('data-copy-text');
            if (textToCopy) {
                copyToClipboard(textToCopy, this);
            }
        });
    });
}









