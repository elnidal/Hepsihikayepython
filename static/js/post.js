function ratePost(postId, isLike) {
    const action = isLike ? 'like' : 'dislike';
    fetch(`/post/${postId}/rate/${action}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update like/dislike counts
            document.getElementById(`likes-${postId}`).textContent = data.likes;
            document.getElementById(`dislikes-${postId}`).textContent = data.dislikes;
            
            // Show success message
            const messageDiv = document.getElementById('message');
            messageDiv.textContent = 'Oyunuz kaydedildi!';
            messageDiv.className = 'alert alert-success';
            setTimeout(() => {
                messageDiv.style.display = 'none';
            }, 3000);
        } else {
            throw new Error(data.message || 'Bir hata oluştu');
        }
    })
    .catch(error => {
        // Show error message
        const messageDiv = document.getElementById('message');
        messageDiv.textContent = error.message;
        messageDiv.className = 'alert alert-danger';
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 3000);
    });
}
