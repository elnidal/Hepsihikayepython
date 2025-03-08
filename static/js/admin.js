// Admin Panel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Comment deletion handler
    setupCommentDeletion();
});

function setupCommentDeletion() {
    // Find all comment delete forms
    const deleteForms = document.querySelectorAll('.comment-delete-form');
    
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const commentId = this.getAttribute('data-comment-id');
            const csrfToken = document.querySelector('meta[name="csrf-token"]') ? 
                              document.querySelector('meta[name="csrf-token"]').getAttribute('content') : 
                              this.querySelector('input[name="csrf_token"]').value;
            
            // Send the delete request
            fetch(this.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: new URLSearchParams({
                    'csrf_token': csrfToken
                })
            })
            .then(response => {
                if (response.ok) {
                    // Close the modal
                    const modal = document.getElementById(`deleteCommentModal${commentId}`);
                    const modalInstance = bootstrap.Modal.getInstance(modal);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    
                    // Remove the comment row
                    const commentRow = document.querySelector(`tr[data-comment-id="${commentId}"]`);
                    if (commentRow) {
                        commentRow.remove();
                    }
                    
                    // Show success message
                    showAdminMessage('Yorum başarıyla silindi', 'success');
                    
                    // Reload the page after a short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    throw new Error('Yorum silinirken bir hata oluştu');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAdminMessage(error.message, 'danger');
            });
        });
    });
}

function showAdminMessage(message, type) {
    // Create a div for the message if it doesn't exist
    let messageContainer = document.getElementById('admin-message-container');
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.id = 'admin-message-container';
        messageContainer.style.position = 'fixed';
        messageContainer.style.top = '20px';
        messageContainer.style.right = '20px';
        messageContainer.style.zIndex = '9999';
        document.body.appendChild(messageContainer);
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    messageContainer.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => {
            alertDiv.remove();
        }, 150);
    }, 5000);
} 