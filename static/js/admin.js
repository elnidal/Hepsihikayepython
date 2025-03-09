// Admin Panel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Set up delete buttons
    setupDeleteButtons();
    
    // Log for debugging
    console.log('Admin JS loaded');
    console.log('Delete forms found:', document.querySelectorAll('.comment-delete-form').length);
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
        messageElement.classList.remove('show');
        setTimeout(() => {
            messageElement.remove();
        }, 300);
    }, 3000);
} 