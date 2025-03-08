/**
 * AJAX Navigation System for HepsiHikaye
 * 
 * This script handles smooth transitions between pages by loading content via AJAX
 * instead of full page reloads, providing a more app-like experience.
 */

$(document).ready(function() {
    // Initialize AJAX navigation
    initAjaxNavigation();
    
    // Initialize page elements
    initializePageElements();
    
    // Back to top button
    var backToTopBtn = $('#backToTopBtn');
    
    $(window).scroll(function() {
        if ($(this).scrollTop() > 300) {
            backToTopBtn.addClass('visible');
        } else {
            backToTopBtn.removeClass('visible');
        }
    });
    
    backToTopBtn.click(function() {
        $('html, body').animate({scrollTop: 0}, 500);
        return false;
    });
    
    // Mobile-specific: Keep header visible at all times
    var lastScrollTop = 0;
    var delta = 5;
    var navbarHeight = $('.site-header').outerHeight();
    
    $(window).scroll(function() {
        // Always keep the header visible
        $('.site-header').css('transform', 'translateY(0)');
        
        // Update last scroll position
        lastScrollTop = $(this).scrollTop();
    });
    
    // Mobile-specific: Active state for bottom navigation
    $('.mobile-nav-item').on('click', function() {
        $('.mobile-nav-item').removeClass('active');
        $(this).addClass('active');
    });
});

/**
 * Initialize AJAX navigation
 */
function initAjaxNavigation() {
    // Attach click handlers to all internal links
    $(document).on('click', 'a[href^="/"]:not([data-no-ajax])', function(e) {
        var href = $(this).attr('href');
        
        // Skip if it's an admin link, login, logout, or has data-no-ajax attribute
        if (href.indexOf('/admin') === 0 || 
            href.indexOf('/login') === 0 || 
            href.indexOf('/logout') === 0 || 
            $(this).attr('data-no-ajax')) {
            return true;
        }
        
        e.preventDefault();
        
        // Load the content via AJAX
        loadContent(href, true);
    });
    
    // Handle browser back/forward buttons
    $(window).on('popstate', function(e) {
        if (e.originalEvent.state) {
            loadContent(location.pathname, false);
        } else {
            window.location.reload();
        }
    });
    
    // Global AJAX error handling
    $(document).ajaxError(function(event, jqXHR, settings, thrownError) {
        console.error('AJAX Error:', thrownError);
        
        // Show appropriate error message based on status code
        if (jqXHR.status === 404) {
            showNotification('Sayfa bulunamadı (404)', 'error');
        } else if (jqXHR.status === 500) {
            showNotification('Sunucu hatası (500)', 'error');
        } else if (jqXHR.status === 0) {
            showNotification('Bağlantı hatası. İnternet bağlantınızı kontrol edin.', 'error');
        } else {
            showNotification('Bir hata oluştu: ' + thrownError, 'error');
        }
    });
}

/**
 * Load content via AJAX
 * @param {string} url - The URL to load
 * @param {boolean} pushState - Whether to push state to browser history
 */
function loadContent(url, pushState) {
    // Show loading indicator
    showLoadingIndicator();
    
    $.ajax({
        url: url,
        type: 'GET',
        dataType: 'html',
        timeout: 10000, // 10 second timeout
        success: function(data) {
            // Extract the content
            var $data = $(data);
            var $newContent = $data.find('.page-content');
            
            // If content was found
            if ($newContent.length) {
                // Update the page title
                var newTitle = $data.filter('title').text();
                document.title = newTitle;
                
                // Update the URL if needed
                if (pushState) {
                    history.pushState({url: url}, newTitle, url);
                }
                
                // Update active state in navigation
                updateActiveNavigation(url);
                
                // Fade out current content
                $('.page-content').fadeOut(200, function() {
                    // Replace with new content
                    $(this).html($newContent.html()).fadeIn(200);
                    
                    // Reinitialize page elements
                    initializePageElements();
                    
                    // Scroll to top
                    window.scrollTo(0, 0);
                    
                    // Hide loading indicator
                    hideLoadingIndicator();
                });
            } else {
                // If content wasn't found, redirect
                window.location = url;
            }
        },
        error: function(xhr, status, error) {
            console.error('AJAX error:', status, error);
            
            // Show error notification
            showNotification('Sayfa yüklenirken bir hata oluştu. Yeniden deneniyor...', 'error');
            
            // Redirect after a short delay
            setTimeout(function() {
                window.location = url;
            }, 1500);
        }
    });
}

/**
 * Update active state in navigation
 * @param {string} url - The current URL
 */
function updateActiveNavigation(url) {
    // Remove active class from all navigation items
    $('.nav-category').removeClass('active');
    $('.mobile-nav-item').removeClass('active');
    
    // Add active class to matching navigation items
    $('.nav-category[href="' + url + '"]').addClass('active');
    $('.mobile-nav-item[href="' + url + '"]').addClass('active');
    
    // Handle category pages
    if (url.indexOf('/category/') === 0) {
        var category = url.split('/').pop();
        $('.nav-category[href^="/category/' + category + '"]').addClass('active');
        $('.mobile-nav-item[href^="/category/' + category + '"]').addClass('active');
    }
}

/**
 * Initialize page elements
 */
function initializePageElements() {
    // Initialize any JavaScript that needs to run on new content
    
    // Lazy load images
    lazyLoadImages();
    
    // Handle image errors
    handleImageErrors();
    
    // Attach pagination handlers
    attachPaginationHandlers();
    
    // Initialize any other components
}

/**
 * Show loading indicator
 */
function showLoadingIndicator() {
    $('#ajax-loader .spinner').css('width', '30%');
    
    // Animate to 70% to simulate progress
    setTimeout(function() {
        $('#ajax-loader .spinner').css('width', '70%');
    }, 500);
}

/**
 * Hide loading indicator
 */
function hideLoadingIndicator() {
    $('#ajax-loader .spinner').css('width', '100%');
    
    // Reset after transition completes
    setTimeout(function() {
        $('#ajax-loader .spinner').css('width', '0');
    }, 300);
}

/**
 * Show notification
 * @param {string} message - The notification message
 * @param {string} type - The notification type (success, error, warning, info)
 */
function showNotification(message, type) {
    // Create notification element if it doesn't exist
    if ($('#notification').length === 0) {
        $('body').append('<div id="notification"></div>');
    }
    
    // Set notification content and type
    $('#notification')
        .attr('class', type)
        .html(message)
        .fadeIn(300);
    
    // Hide notification after 3 seconds
    setTimeout(function() {
        $('#notification').fadeOut(300);
    }, 3000);
}

/**
 * Lazy load images
 */
function lazyLoadImages() {
    // Check if IntersectionObserver is supported
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                // If the image is in the viewport
                if (entry.isIntersecting) {
                    const img = entry.target;
                    const src = img.getAttribute('data-src');
                    
                    // Only replace if data-src exists
                    if (src) {
                        // Add a load event to handle fade-in animation
                        img.onload = function() {
                            img.classList.add('loaded');
                        };
                        
                        // Set the src to load the image
                        img.src = src;
                        
                        // Remove the data-src attribute to prevent future loading
                        img.removeAttribute('data-src');
                        
                        // Stop observing the image
                        observer.unobserve(img);
                    }
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.01
        });
        
        // Find all images with data-src attribute
        const lazyImages = document.querySelectorAll('img[data-src]');
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    } else {
        // Fallback for browsers that don't support IntersectionObserver
        const lazyImages = document.querySelectorAll('img[data-src]');
        lazyImages.forEach(img => {
            const src = img.getAttribute('data-src');
            if (src) {
                img.src = src;
                img.removeAttribute('data-src');
            }
        });
    }
    
    // Convert regular images to lazy-loaded images
    convertToLazyImages();
}

/**
 * Convert regular images to lazy-loaded images
 */
function convertToLazyImages() {
    // Find all images that don't have data-src and aren't already processed
    const images = document.querySelectorAll('img:not([data-src]):not(.lazy-converted)');
    
    images.forEach(img => {
        // Skip images without src
        if (!img.src) return;
        
        // Mark as converted
        img.classList.add('lazy-converted');
        
        // If the image is already loaded, don't modify it
        if (img.complete && img.naturalHeight !== 0) {
            img.classList.add('loaded');
            return;
        }
        
        // Store the original src
        const src = img.src;
        
        // Set a placeholder or low-quality image
        img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"%3E%3C/svg%3E';
        
        // Set data-src to the original src
        img.setAttribute('data-src', src);
        
        // Add lazy-load class for styling
        img.classList.add('lazy-load');
    });
}

/**
 * Attach pagination handlers
 */
function attachPaginationHandlers() {
    // Attach AJAX navigation to pagination links
    $('.pagination .page-link').on('click', function(e) {
        var href = $(this).attr('href');
        
        if (href) {
            e.preventDefault();
            loadContent(href, true);
        }
    });
}

/**
 * Handle image loading errors
 */
function handleImageErrors() {
    // Find all images
    const images = document.querySelectorAll('img');
    
    images.forEach(img => {
        // Skip images that already have an error handler
        if (img.hasAttribute('data-error-handled')) return;
        
        // Mark as handled
        img.setAttribute('data-error-handled', 'true');
        
        // Add error handler
        img.addEventListener('error', function() {
            // Replace with default image
            this.src = '/static/img/default-story.jpg';
            this.classList.add('error-image');
            
            // Log error
            console.warn('Image failed to load:', this.getAttribute('data-src') || this.src);
        });
    });
} 