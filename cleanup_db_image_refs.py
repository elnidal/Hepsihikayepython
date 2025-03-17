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

def cleanup_database_image_references():
    """Clean up image references in the database"""
    logger.info("Starting cleanup of database image references...")
    
    try:
        # Standardize image_url format
        posts = Post.query.filter(Post.image_url.isnot(None)).all()
        logger.info(f"Found {len(posts)} posts with image URLs")
        
        updated_count = 0
        
        for post in posts:
            if not post.image_url:
                continue
            
            # Check if image_url starts with 'uploads/'
            if post.image_url.startswith('uploads/'):
                # Remove 'uploads/' prefix
                post.image_url = post.image_url.replace('uploads/', '', 1)
                updated_count += 1
                logger.info(f"Post ID {post.id}: Removed 'uploads/' prefix from image URL")
            
            # Check if image_url starts with 'static/uploads/'
            if post.image_url.startswith('static/uploads/'):
                # Remove 'static/uploads/' prefix
                post.image_url = post.image_url.replace('static/uploads/', '', 1)
                updated_count += 1
                logger.info(f"Post ID {post.id}: Removed 'static/uploads/' prefix from image URL")
            
            # Check for empty image_url
            if post.image_url.strip() == '':
                post.image_url = 'default_post_image.png'
                updated_count += 1
                logger.info(f"Post ID {post.id}: Set empty image URL to default image")
                
        # Commit changes if any
        if updated_count > 0:
            db.session.commit()
            logger.info(f"Updated {updated_count} posts with standardized image URLs")
        
        # Add statistics
        logger.info("Image URL distribution in database:")
        distribution = {}
        posts = Post.query.filter(Post.image_url.isnot(None)).all()
        
        for post in posts:
            if not post.image_url:
                continue
                
            image_url = post.image_url
            if image_url in distribution:
                distribution[image_url] += 1
            else:
                distribution[image_url] = 1
        
        for image_url, count in distribution.items():
            logger.info(f"  {image_url}: {count} posts")
            
    except Exception as e:
        logger.error(f"Error cleaning up database image references: {str(e)}")
        db.session.rollback()

if __name__ == "__main__":
    with app.app_context():
        cleanup_database_image_references() 