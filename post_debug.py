#!/usr/bin/env python3
import os
import sys
from flask import render_template
from app import app, db, Post
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def check_post(post_id):
    """Check if a post exists and can be rendered"""
    logger.info(f"Checking post with ID {post_id}...")
    
    with app.app_context():
        # Check if post exists
        post = Post.query.get(post_id)
        
        if not post:
            logger.error(f"❌ Post with ID {post_id} does not exist in the database")
            return
            
        logger.info(f"✅ Found post: ID={post.id}, Title='{post.title}'")
        logger.info(f"   Category: {post.category}")
        logger.info(f"   Author: {post.author}")
        logger.info(f"   Image URL: {post.image_url}")
        logger.info(f"   Content length: {len(post.content)} characters")
        
        # Check if post has valid content
        if not post.content:
            logger.error(f"❌ Post has empty content")
        elif len(post.content) < 10:
            logger.warning(f"⚠️ Post has very short content: '{post.content}'")
            
        # Try to render the post template with minimal context
        try:
            logger.info("Attempting minimal rendering...")
            rendered = render_template(
                'simple_post.html',
                post=post
            )
            logger.info(f"✅ Successfully rendered minimal template ({len(rendered)} characters)")
        except Exception as e:
            logger.error(f"❌ Error rendering minimal template: {str(e)}")
            logger.error(traceback.format_exc())
            
        # Try to render the actual post template
        try:
            logger.info("Attempting to render actual post_detail.html template...")
            rendered = render_template(
                'post_detail.html',
                post=post
            )
            logger.info(f"✅ Successfully rendered post_detail.html ({len(rendered)} characters)")
        except Exception as e:
            logger.error(f"❌ Error rendering post_detail.html: {str(e)}")
            logger.error(traceback.format_exc())

def check_all_posts():
    """Check all posts in the database"""
    logger.info("Checking all posts...")
    
    with app.app_context():
        # Get all posts
        posts = Post.query.all()
        logger.info(f"Found {len(posts)} posts in the database")
        
        # Display basic info for all posts
        for post in posts:
            logger.info(f"Post {post.id}: '{post.title}' (Category: {post.category})")

if __name__ == "__main__":
    # Create a simple post template file for testing
    simple_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ post.title }}</title>
    </head>
    <body>
        <h1>{{ post.title }}</h1>
        <p>Category: {{ post.get_category_display() }}</p>
        <p>Author: {{ post.author }}</p>
        <div>{{ post.content|safe }}</div>
    </body>
    </html>
    """
    
    simple_template_path = os.path.join(app.template_folder, 'simple_post.html')
    with open(simple_template_path, 'w') as f:
        f.write(simple_template)
    logger.info(f"Created simple test template at {simple_template_path}")
    
    # Check post with ID 7 (the one that's failing)
    check_post(7)
    
    # Check all posts to see if there are issues with others
    check_all_posts() 