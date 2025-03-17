import os
import sys
import logging
from app import app, db, Post
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_file_exists(file_path):
    """Check if a file exists at the given path"""
    return os.path.isfile(file_path)

def check_and_fix_missing_uploads():
    """Check for missing upload files and fix database references"""
    logger.info("Starting check for missing upload files...")
    
    # Get upload directory path
    upload_dir = app.config.get('UPLOAD_FOLDER', 'static/uploads')
    if not os.path.isdir(upload_dir):
        logger.error(f"Upload directory {upload_dir} does not exist!")
        return
    
    # Default image path
    default_image = 'static/uploads/default_post_image.png'
    
    # Check if default image exists
    if not check_file_exists(default_image):
        logger.warning(f"Default image {default_image} does not exist!")
    
    # Get all posts with image_url
    try:
        posts = Post.query.filter(Post.image_url.isnot(None)).all()
        logger.info(f"Found {len(posts)} posts with image URLs")
        
        missing_count = 0
        fixed_count = 0
        
        for post in posts:
            if not post.image_url:
                continue
                
            # Get the full path to the image
            image_path = None
            
            # Check different possible paths
            possible_paths = [
                # Direct path as stored
                post.image_url,
                # Path in uploads directory
                os.path.join(upload_dir, post.image_url),
                # Path with static prefix
                os.path.join('static/uploads', post.image_url)
            ]
            
            # Try to find the file
            for path in possible_paths:
                if check_file_exists(path):
                    image_path = path
                    break
            
            # If image doesn't exist
            if not image_path:
                logger.warning(f"Post ID {post.id}: Image '{post.image_url}' not found")
                missing_count += 1
                
                # Update the post to use default image
                post.image_url = 'default_post_image.png'
                fixed_count += 1
                logger.info(f"Post ID {post.id}: Updated to use default image")
        
        # Commit changes if any
        if fixed_count > 0:
            db.session.commit()
            logger.info(f"Fixed {fixed_count} posts with missing images")
        
        logger.info(f"Summary: {missing_count} missing images found, {fixed_count} posts updated")
    
    except Exception as e:
        logger.error(f"Error checking posts: {str(e)}")
        db.session.rollback()

if __name__ == "__main__":
    with app.app_context():
        check_and_fix_missing_uploads() 