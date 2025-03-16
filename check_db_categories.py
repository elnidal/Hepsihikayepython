#!/usr/bin/env python3
import os
import sys
import logging
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
    category = db.Column(db.String(50), nullable=False, index=True)

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

def check_categories():
    """Check categories in the database"""
    try:
        print("Categories defined in app:")
        for slug, name in CATEGORIES:
            print(f"  - {slug}: {name}")
        
        with app.app_context():
            # Get total post count
            total_posts = Post.query.count()
            print(f"\nTotal posts in database: {total_posts}")
            
            # Get categories with post counts
            category_counts = db.session.query(
                Post.category, 
                func.count(Post.id).label('count')
            ).group_by(Post.category).all()
            
            print(f"\nCategories found in posts: {len(category_counts)}")
            for category, count in category_counts:
                # Get the display name for the category
                category_dict = dict(CATEGORIES)
                display_name = category_dict.get(category, category.capitalize())
                print(f"  - {category} ({display_name}): {count} posts")
            
            # List all posts with their categories
            print("\nAll posts in database:")
            posts = Post.query.all()
            for post in posts:
                print(f"  - ID: {post.id}, Title: {post.title}, Category: {post.category}")
                
    except Exception as e:
        logger.error(f"Error checking categories: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    return True

if __name__ == "__main__":
    check_categories() 