function ratePost(postId, isLike) {
    const action = isLike ? 'like' : 'dislike';
    
    // Log to help with debugging
    console.log(`Attempting to rate post ${postId} with action ${action}`);
    
    // Basic fetch request with minimal options
    fetch(`/post/${postId}/rate/${action}`, {
        method: 'POST',
        credentials: 'same-origin'
    })
    .then(response => {
        console.log(`Server responded with status: ${response.status}`);
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        if (data.success) {
            // Update the like/dislike counts in the UI
            const likesElement = document.getElementById(`likes-${postId}`);
            const dislikesElement = document.getElementById(`dislikes-${postId}`);
            
            console.log('Elements:', likesElement, dislikesElement);
            
            if (likesElement) {
                likesElement.textContent = data.likes;
                console.log(`Updated likes to ${data.likes}`);
            }
            
            if (dislikesElement) {
                dislikesElement.textContent = data.dislikes;
                console.log(`Updated dislikes to ${data.dislikes}`);
            }
            
            // Show feedback
            alert('Oyunuz kaydedildi!');
        } else {
            alert(data.message || 'Bir hata oluştu');
        }
    })
    .catch(error => {
        console.error('Error rating post:', error);
        alert('Bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
    });
}

// Helper function to show feedback messages - simplified to ensure it works
function showFeedback(message, type) {
    alert(message);
}

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Animate story cards on page load
    animateStoryCards();
    
    // Handle image loading
    handleImageLoading();
    
    // Add touch swipe support for mobile
    addTouchSupport();
    
    // Add smooth scrolling for anchor links
    addSmoothScrolling();
    
    // Initialize rating buttons
    initRatingButtons();
});

// Animate story cards with a staggered effect
function animateStoryCards() {
    const storyCards = document.querySelectorAll('.story-card, .category-post-item');
    
    storyCards.forEach((card, index) => {
        // Add animation classes with delay based on index
        card.classList.add('animate-card');
        card.classList.add(`delay-${(index % 8) + 1}`);
        
        // Add hover effect
        card.classList.add('hover-card');
    });
}

// Handle image loading states
function handleImageLoading() {
    const images = document.querySelectorAll('.story-image, .post-image img, .category-post-image');
    
    images.forEach(img => {
        // Check if image is already loaded (for cached images)
        if (img.complete) {
            img.classList.remove('image-loading');
            img.classList.add('image-loaded');
            return;
        }
        
        // Set initial state
        img.classList.add('image-loading');
        
        // When image loads successfully
        img.addEventListener('load', function() {
            img.classList.remove('image-loading');
            img.classList.add('image-loaded');
        });
        
        // Handle loading errors
        img.addEventListener('error', function() {
            img.classList.remove('image-loading');
            // Optionally add a class for error state or replace with a placeholder
            img.src = '/static/img/default-story.jpg';
        });
    });
}

// Add touch swipe support for mobile navigation
function addTouchSupport() {
    // Only initialize on mobile devices
    if (window.innerWidth <= 768) {
        const navCategories = document.querySelector('.nav-categories');
        
        if (navCategories) {
            let startX, startY, endX, endY;
            let isScrolling = false;
            
            navCategories.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            }, false);
            
            navCategories.addEventListener('touchmove', function(e) {
                if (!startX || !startY) return;
                
                endX = e.touches[0].clientX;
                endY = e.touches[0].clientY;
                
                // Determine if scrolling horizontally or vertically
                if (!isScrolling) {
                    isScrolling = Math.abs(endX - startX) > Math.abs(endY - startY);
                    
                    // If scrolling horizontally, prevent default to avoid page scrolling
                    if (isScrolling) {
                        e.preventDefault();
                    }
                }
            }, { passive: false });
            
            navCategories.addEventListener('touchend', function() {
                startX = startY = endX = endY = null;
                isScrolling = false;
            }, false);
        }
    }
}

// Add smooth scrolling for anchor links
function addSmoothScrolling() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]:not([href="#"])');
    
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                // Smooth scroll to target
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update URL hash without scrolling
                history.pushState(null, null, targetId);
            }
        });
    });
}

// Initialize rating buttons
function initRatingButtons() {
    const ratingButtons = document.querySelectorAll('.rating-buttons .btn');
    
    ratingButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Get the button group
            const buttonGroup = this.closest('.rating-buttons');
            
            // Remove active class from all buttons in the group
            buttonGroup.querySelectorAll('.btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Add active class to clicked button
            this.classList.add('active');
        });
    });
}

// Improve responsiveness for mobile devices
window.addEventListener('resize', function() {
    // Adjust elements based on screen size
    if (window.innerWidth <= 768) {
        // Mobile optimizations
        optimizeForMobile();
    } else {
        // Desktop optimizations
        optimizeForDesktop();
    }
});

// Mobile-specific optimizations
function optimizeForMobile() {
    // Adjust image heights for better mobile viewing
    const storyImages = document.querySelectorAll('.story-image');
    storyImages.forEach(img => {
        img.style.height = '180px';
    });
    
    // Make tables responsive
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        if (!table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
}

// Desktop-specific optimizations
function optimizeForDesktop() {
    // Reset image heights
    const storyImages = document.querySelectorAll('.story-image');
    storyImages.forEach(img => {
        img.style.height = '';
    });
}

// Initialize based on current screen size
if (window.innerWidth <= 768) {
    optimizeForMobile();
} else {
    optimizeForDesktop();
}

// Add lazy loading for images
document.addEventListener('DOMContentLoaded', function() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    const src = img.getAttribute('data-src');
                    
                    if (src) {
                        img.src = src;
                        img.removeAttribute('data-src');
                    }
                    
                    observer.unobserve(img);
                }
            });
        });
        
        // Target all images with data-src attribute
        const lazyImages = document.querySelectorAll('img[data-src]');
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    } else {
        // Fallback for browsers that don't support IntersectionObserver
        const lazyImages = document.querySelectorAll('img[data-src]');
        lazyImages.forEach(img => {
            img.src = img.getAttribute('data-src');
            img.removeAttribute('data-src');
        });
    }
});
