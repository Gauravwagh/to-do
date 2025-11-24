// Material Design JavaScript for Evernote Clone

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Materialize components
    initializeMaterialize();
    
    // Initialize TinyMCE
    initializeTinyMCE();
    
    // Initialize custom functionality
    initializeCustomFeatures();
});

function initializeMaterialize() {
    // Initialize Sidenav
    const sidenavElements = document.querySelectorAll('.sidenav');
    M.Sidenav.init(sidenavElements);
    
    // Initialize Dropdown
    const dropdownElements = document.querySelectorAll('.dropdown-trigger');
    M.Dropdown.init(dropdownElements, {
        coverTrigger: false,
        constrainWidth: false
    });
    
    // Initialize Modals
    const modalElements = document.querySelectorAll('.modal');
    M.Modal.init(modalElements);
    
    // Initialize Tooltips
    const tooltipElements = document.querySelectorAll('.tooltipped');
    M.Tooltip.init(tooltipElements);
    
    // Initialize Floating Action Button
    const fabElements = document.querySelectorAll('.fixed-action-btn');
    M.FloatingActionButton.init(fabElements);
    
    // Initialize Collapsible
    const collapsibleElements = document.querySelectorAll('.collapsible');
    M.Collapsible.init(collapsibleElements);
    
    // Initialize Tabs
    const tabElements = document.querySelectorAll('.tabs');
    M.Tabs.init(tabElements);
    
    // Initialize Select
    const selectElements = document.querySelectorAll('select');
    M.FormSelect.init(selectElements);
    
    // Initialize Date Picker
    const datePickerElements = document.querySelectorAll('.datepicker');
    M.Datepicker.init(datePickerElements, {
        format: 'yyyy-mm-dd',
        autoClose: true
    });
    
    // Initialize Time Picker
    const timePickerElements = document.querySelectorAll('.timepicker');
    M.Timepicker.init(timePickerElements, {
        twelveHour: false
    });
}

function initializeTinyMCE() {
    // Initialize TinyMCE for rich text editing
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: '.tinymce-editor',
            height: 400,
            width: '100%',
            menubar: false,
            plugins: [
                'advlist autolink lists link image charmap print preview anchor',
                'searchreplace visualblocks code fullscreen',
                'insertdatetime media table contextmenu paste code'
            ],
            toolbar: 'undo redo | formatselect | bold italic backcolor | ' +
                     'alignleft aligncenter alignright alignjustify | ' +
                     'bullist numlist outdent indent | removeformat | help',
            content_style: 'body { font-family: "Roboto", sans-serif; font-size: 14px; }',
            branding: false,
            statusbar: true,
            resize: true,
            setup: function (editor) {
                editor.on('change', function () {
                    editor.save();
                });
            }
        });
    }
}

function initializeCustomFeatures() {
    // Close message functionality
    initializeMessageClose();
    
    // Initialize clipboard functionality
    initializeClipboard();
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize card interactions
    initializeCardInteractions();
    
    // Initialize todo functionality
    initializeTodoFeatures();
}

function initializeMessageClose() {
    // Add close functionality to messages
    const closeButtons = document.querySelectorAll('.close-message');
    closeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const message = this.closest('.card-panel');
            if (message) {
                message.style.transition = 'opacity 0.3s ease';
                message.style.opacity = '0';
                setTimeout(() => {
                    message.remove();
                }, 300);
            }
        });
    });
}

function initializeClipboard() {
    // Copy to clipboard functionality
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
    
    buttonElement.innerHTML = '<i class="material-icons left">check</i>Copied!';
    buttonElement.className = originalClass.replace('btn-outline', 'btn');
    buttonElement.classList.add('green');
    
    setTimeout(() => {
        buttonElement.innerHTML = originalText;
        buttonElement.className = originalClass;
    }, 2000);
}

function showCopyError(buttonElement) {
    const originalText = buttonElement.innerHTML;
    const originalClass = buttonElement.className;
    
    buttonElement.innerHTML = '<i class="material-icons left">error</i>Failed';
    buttonElement.className = originalClass.replace('btn-outline', 'btn');
    buttonElement.classList.add('red');
    
    setTimeout(() => {
        buttonElement.innerHTML = originalText;
        buttonElement.className = originalClass;
    }, 2000);
}

function initializeSearch() {
    // Enhanced search functionality
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            const cards = document.querySelectorAll('.note-card, .notebook-card');
            
            cards.forEach(card => {
                const title = card.querySelector('.card-title');
                const content = card.querySelector('.card-content p');
                
                if (title || content) {
                    const titleText = title ? title.textContent.toLowerCase() : '';
                    const contentText = content ? content.textContent.toLowerCase() : '';
                    
                    if (titleText.includes(query) || contentText.includes(query)) {
                        card.style.display = 'block';
                        card.classList.add('fade-in');
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
        });
    }
}

function initializeCardInteractions() {
    // Add hover effects and click interactions to cards
    const cards = document.querySelectorAll('.note-card, .notebook-card, .todo-card');
    
    cards.forEach(card => {
        // Add ripple effect on click
        card.addEventListener('click', function(e) {
            if (!e.target.closest('a, button')) {
                createRipple(e, this);
            }
        });
        
        // Add hover effects
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

function createRipple(event, element) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.classList.add('ripple');
    
    element.appendChild(ripple);
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

function initializeTodoFeatures() {
    // Todo checkbox functionality
    const todoCheckboxes = document.querySelectorAll('.todo-checkbox');
    todoCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const todoId = this.value;
            const isCompleted = this.checked;
            
            // Update visual state
            const card = this.closest('.todo-card');
            if (card) {
                if (isCompleted) {
                    card.classList.add('completed');
                } else {
                    card.classList.remove('completed');
                }
            }
            
            // You can add AJAX functionality here to save the state
            // For now, we'll just update the visual state
        });
    });
}

// Utility functions
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Initialize and show toast
    M.toast({html: message, classes: type});
}

function showLoading(element) {
    const loading = document.createElement('div');
    loading.className = 'progress';
    loading.innerHTML = '<div class="indeterminate"></div>';
    
    element.appendChild(loading);
}

function hideLoading(element) {
    const loading = element.querySelector('.progress');
    if (loading) {
        loading.remove();
    }
}

// Add CSS for ripple effect
const style = document.createElement('style');
style.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        background-color: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple-animation 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .note-card, .notebook-card, .todo-card {
        position: relative;
        overflow: hidden;
    }
`;
document.head.appendChild(style);
