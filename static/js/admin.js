// Admin Panel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
    
    // Initialize any datepickers
    const datepickers = document.querySelectorAll('.datepicker');
    if (datepickers.length > 0) {
        datepickers.forEach(dp => {
            new Datepicker(dp, {
                format: 'dd.mm.yyyy',
                language: 'tr',
                autohide: true
            });
        });
    }
    
    // Initialize select2 if available
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            theme: 'bootstrap-5'
        });
    }
    
    // Add form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Handle sidebar toggle for mobile
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            document.querySelector('.admin-sidebar').classList.toggle('show');
        });
    }
    
    // Handle alert dismissal
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.remove();
            });
        }
    });
    
    // Set up delete buttons if they exist
    if (document.querySelectorAll('.comment-delete-form').length > 0) {
        setupDeleteButtons();
    }
    
    // Log for debugging
    console.log('Admin JS loaded');
});

function setupDeleteButtons() {
    console.log('Setting up delete buttons');
    
    // Get all delete forms
    const deleteForms = document.querySelectorAll('.comment-delete-form');
    
    deleteForms.forEach(form => {
        console.log('Setting up form:', form);
        
        form.addEventListener('submit', function(e) {
            console.log('Delete form submitted');
            
            // Prevent default form submission
            e.preventDefault();
            
            const commentId = form.getAttribute('data-comment-id');
            console.log('Comment ID:', commentId);
            
            // Close the modal
            const modal = form.closest('.modal');
            if (modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            }
            
            // Manually submit with fetch
            performDelete(form.action, commentId);
        });
    });
    
    // Also handle direct button clicks as a fallback
    const deleteButtons = document.querySelectorAll('.modal .btn-danger');
    deleteButtons.forEach(button => {
        // Only handle buttons inside forms
        if (button.closest('form.comment-delete-form')) {
            button.addEventListener('click', function(e) {
                console.log('Delete button clicked directly');
                
                // The form's submit event should handle this, but as a fallback:
                const form = button.closest('form.comment-delete-form');
                if (form) {
                    e.preventDefault();
                    
                    const commentId = form.getAttribute('data-comment-id');
                    console.log('Comment ID from button click:', commentId);
                    
                    // Close the modal
                    const modal = button.closest('.modal');
                    if (modal) {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) {
                            bsModal.hide();
                        }
                    }
                    
                    // Manually submit with fetch
                    performDelete(form.action, commentId);
                }
            });
        }
    });
}

function performDelete(url, commentId) {
    console.log('Performing delete for comment:', commentId, 'URL:', url);
    
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: `csrf_token=${csrfToken}`,
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('Delete response status:', response.status);
        if (response.redirected) {
            window.location = response.url;
            return;
        }
        
        if (!response.ok) {
            throw new Error('Delete failed: ' + response.status);
        }
        
        return response.json();
    })
    .then(data => {
        console.log('Delete response data:', data);
        
        // Remove the row from the table
        const row = document.querySelector(`tr[data-comment-id="${commentId}"]`);
        if (row) {
            row.remove();
            showMessage('Yorum başarıyla silindi', 'success');
        } else {
            showMessage('Yorum silindi, ancak sayfayı yenilemek gerekiyor', 'success');
            // Reload after short delay
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        }
    })
    .catch(error => {
        console.error('Error deleting comment:', error);
        showMessage('Bir hata oluştu: ' + error.message, 'danger');
    });
}

function showMessage(message, type) {
    // Create a div for the message
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    messageElement.style.top = '20px';
    messageElement.style.right = '20px';
    messageElement.style.zIndex = '9999';
    messageElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to document
    document.body.appendChild(messageElement);
    
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        if (messageElement) {
            messageElement.classList.remove('show');
            setTimeout(() => {
                messageElement.remove();
            }, 300);
        }
    }, 3000);
}

// Utility functions for admin panel
const AdminUtils = {
    // Show loading spinner
    showLoading: function(element) {
        if (element) {
            element.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Yükleniyor...';
            element.disabled = true;
        }
    },
    
    // Hide loading spinner
    hideLoading: function(element, originalText) {
        if (element) {
            element.innerHTML = originalText;
            element.disabled = false;
        }
    },
    
    // Show toast notification
    showToast: function(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        document.getElementById('toast-container').appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    },
    
    // Format date for display
    formatDate: function(date) {
        return new Date(date).toLocaleDateString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    },
    
    // Format number for display
    formatNumber: function(number) {
        return new Intl.NumberFormat('tr-TR').format(number);
    },
    
    // Confirm action
    confirm: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },
    
    // Handle AJAX errors
    handleAjaxError: function(error) {
        console.error('AJAX Error:', error);
        this.showToast('Bir hata oluştu. Lütfen tekrar deneyin.', 'danger');
    }
};

// Export AdminUtils for use in other files
window.AdminUtils = AdminUtils; 