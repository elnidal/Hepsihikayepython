#!/usr/bin/env python3
import os
import sys
import logging
import shutil
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a minimal Flask app for database access
app = Flask(__name__)

# Load environment variables from .env file if present
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///hepsihikaye.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Post model minimally
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    image_url = db.Column(db.String(500))

# Define categories
CATEGORIES = [
    ('öykü', 'Öykü'),
    ('roman', 'Roman'),
    ('şiir', 'Şiir'),
    ('deneme', 'Deneme'),
    ('inceleme', 'İnceleme'),
    ('haber', 'Haber'),
    ('video', 'Video'),
]

def fix_categories():
    """Fix categories in the database"""
    try:
        with app.app_context():
            # Get all posts
            posts = Post.query.all()
            logger.info(f"Found {len(posts)} posts in database")
            
            # Check each post's category
            fixed_count = 0
            for post in posts:
                # Check if the category is valid
                valid_categories = [slug for slug, _ in CATEGORIES]
                if post.category not in valid_categories:
                    logger.info(f"Post ID {post.id} has invalid category: '{post.category}'")
                    
                    # Set a default category
                    old_category = post.category
                    post.category = 'öykü'  # Default to 'öykü'
                    fixed_count += 1
                    logger.info(f"Updated post ID {post.id} category from '{old_category}' to '{post.category}'")
            
            # Commit changes if any
            if fixed_count > 0:
                db.session.commit()
                logger.info(f"Fixed {fixed_count} posts with invalid categories")
            else:
                logger.info("All posts have valid categories")
                
            return True
            
    except Exception as e:
        logger.error(f"Error fixing categories: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        if 'db' in locals() and db.session:
            db.session.rollback()
        return False

def fix_image_paths():
    """Fix image paths in the database and copy images to static/uploads"""
    try:
        # Ensure static/uploads directory exists
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
            logger.info(f"Created uploads directory at: {uploads_dir}")
        
        # Create default image if it doesn't exist
        default_image_path = os.path.join(uploads_dir, 'default_post_image.png')
        if not os.path.exists(default_image_path):
            logger.info("Default image not found, will use placeholder")
            
        with app.app_context():
            # Get all posts with images
            posts_with_images = Post.query.filter(Post.image_url != None, Post.image_url != '').all()
            logger.info(f"Found {len(posts_with_images)} posts with images")
            
            # Check each post's image path
            fixed_count = 0
            for post in posts_with_images:
                original_image = post.image_url
                logger.info(f"Checking post ID {post.id} with image: {original_image}")
                
                # Extract just the filename from the path
                filename = os.path.basename(original_image)
                
                # Update the path to use static/uploads
                if not filename.startswith('uploads/'):
                    # Update to point to the static/uploads directory
                    post.image_url = f"uploads/{filename}"
                    fixed_count += 1
                    logger.info(f"Updated post ID {post.id} image from '{original_image}' to '{post.image_url}'")
                    
                    # Try to copy the image file if it exists in the old location
                    old_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', filename)
                    new_path = os.path.join(uploads_dir, filename)
                    
                    if os.path.exists(old_path) and not os.path.exists(new_path):
                        try:
                            shutil.copy2(old_path, new_path)
                            logger.info(f"Copied image from {old_path} to {new_path}")
                        except Exception as e:
                            logger.error(f"Error copying image: {str(e)}")
            
            # Commit changes if any
            if fixed_count > 0:
                db.session.commit()
                logger.info(f"Fixed {fixed_count} posts with incorrect image paths")
            else:
                logger.info("All posts have correct image paths")
                
            return True
            
    except Exception as e:
        logger.error(f"Error fixing image paths: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        if 'db' in locals() and db.session:
            db.session.rollback()
        return False

def check_categories_after_fix():
    """Check categories after fixing"""
    try:
        with app.app_context():
            # Get categories with post counts
            category_counts = db.session.query(
                Post.category, 
                func.count(Post.id).label('count')
            ).group_by(Post.category).all()
            
            logger.info(f"Categories after fix: {len(category_counts)}")
            for category, count in category_counts:
                # Get the display name for the category
                category_dict = dict(CATEGORIES)
                display_name = category_dict.get(category, category.capitalize())
                logger.info(f"  - {category} ({display_name}): {count} posts")
                
            return True
            
    except Exception as e:
        logger.error(f"Error checking categories after fix: {str(e)}")
        return False

def main():
    """Run all fixes"""
    logger.info("Starting to fix categories and image paths...")
    
    # Step 1: Fix categories
    if fix_categories():
        logger.info("✅ Successfully fixed categories")
    else:
        logger.error("❌ Failed to fix categories")
    
    # Step 2: Fix image paths
    if fix_image_paths():
        logger.info("✅ Successfully fixed image paths")
    else:
        logger.error("❌ Failed to fix image paths")
    
    # Step 3: Check categories after fix
    if check_categories_after_fix():
        logger.info("✅ Successfully verified categories")
    else:
        logger.error("❌ Failed to verify categories")
    
    logger.info("All fixes completed")
    
if __name__ == "__main__":
    main() 