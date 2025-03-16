#!/usr/bin/env python3
import os
import sys
from flask import Flask, render_template, request
from app import app, db, Post, CATEGORIES
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def check_post_rendering():
    """Check if posts can be rendered properly with the template"""
    logger.info("Checking post rendering...")
    
    with app.app_context():
        # Get all posts
        posts = Post.query.all()
        logger.info(f"Found {len(posts)} posts in database")
        
        if not posts:
            logger.error("No posts found in database!")
            return
        
        # Try to create a test request context
        logger.info("Creating test request context...")
        with app.test_request_context():
            # Try rendering each post
            for post in posts:
                try:
                    logger.info(f"Attempting to render post {post.id}: '{post.title}'")
                    
                    # Get related posts
                    related_posts = Post.query.filter(
                        Post.category == post.category,
                        Post.id != post.id
                    ).order_by(Post.created_at.desc()).limit(4).all()
                    
                    # Render the template
                    rendered = render_template(
                        'post_detail.html',
                        post=post,
                        related_posts=related_posts
                    )
                    
                    logger.info(f"✅ Successfully rendered post {post.id}")
                except Exception as e:
                    logger.error(f"❌ Error rendering post {post.id}: {str(e)}")
                    logger.error(traceback.format_exc())

def check_csrf_token():
    """Check if CSRF token can be generated properly"""
    logger.info("Checking CSRF token generation...")
    
    with app.app_context():
        try:
            # Try to create a test request context
            with app.test_request_context():
                from flask_wtf.csrf import generate_csrf
                token = generate_csrf()
                logger.info(f"✅ Successfully generated CSRF token: {token[:10]}...")
        except Exception as e:
            logger.error(f"❌ Error generating CSRF token: {str(e)}")
            logger.error(traceback.format_exc())

def main():
    """Run all debugging checks"""
    logger.info("Starting CSRF and post rendering diagnostics...")
    
    # Check environment variables
    flask_env = os.environ.get('FLASK_ENV', 'not set')
    flask_debug = os.environ.get('FLASK_DEBUG', 'not set')
    logger.info(f"FLASK_ENV: {flask_env}")
    logger.info(f"FLASK_DEBUG: {flask_debug}")
    
    # Check if database has posts
    with app.app_context():
        post_count = Post.query.count()
        logger.info(f"Number of posts in database: {post_count}")
    
    # Check CSRF token generation
    check_csrf_token()
    
    # Check post rendering
    check_post_rendering()
    
    logger.info("Diagnostics complete!")

if __name__ == "__main__":
    main() 