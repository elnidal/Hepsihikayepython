#!/usr/bin/env python3
import os
import sys
import traceback
from flask import Flask, render_template, url_for, request
from app import app, db, Post, CATEGORIES
import logging
from sqlalchemy.exc import SQLAlchemyError
import tempfile

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_static_files():
    """Check if static files exist and are accessible"""
    logger.info("Checking static files...")
    
    # Check CSS files
    css_files = ['css/style.css', 'css/mobile.css']
    for css_file in css_files:
        full_path = os.path.join(app.static_folder, css_file)
        if os.path.exists(full_path):
            logger.info(f"✅ Found CSS file: {full_path}")
        else:
            logger.error(f"❌ Missing CSS file: {full_path}")
    
    # Check JS files
    js_files = ['js/ajax-navigation.js']
    for js_file in js_files:
        full_path = os.path.join(app.static_folder, js_file)
        if os.path.exists(full_path):
            logger.info(f"✅ Found JS file: {full_path}")
        else:
            logger.error(f"❌ Missing JS file: {full_path}")
    
    # Check uploads directory
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    if os.path.exists(uploads_dir) and os.path.isdir(uploads_dir):
        logger.info(f"✅ Found uploads directory: {uploads_dir}")
        # Count files
        files = os.listdir(uploads_dir)
        logger.info(f"   Contains {len(files)} files")
        # Show up to 5 files
        for i, file in enumerate(files[:5]):
            file_path = os.path.join(uploads_dir, file)
            logger.info(f"   - {file} ({os.path.getsize(file_path) / 1024:.1f} KB)")
    else:
        logger.error(f"❌ Missing uploads directory: {uploads_dir}")
        # Try to create it
        try:
            os.makedirs(uploads_dir, exist_ok=True)
            logger.info(f"   Created uploads directory: {uploads_dir}")
        except Exception as e:
            logger.error(f"   Failed to create uploads directory: {str(e)}")

def check_database_categories():
    """Check database categories"""
    logger.info("Checking database categories...")
    
    try:
        # Check categories in CATEGORIES constant
        logger.info(f"Defined categories in app.py: {len(CATEGORIES)}")
        for slug, name in CATEGORIES:
            logger.info(f"   - {slug}: {name}")
        
        # Check categories in posts
        category_counts = db.session.query(
            Post.category, 
            db.func.count(Post.id).label('count')
        ).group_by(Post.category).all()
        
        logger.info(f"Categories found in posts: {len(category_counts)}")
        for category, count in category_counts:
            logger.info(f"   - {category}: {count} posts")
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())

def check_template_variables():
    """Check template variables"""
    logger.info("Checking template variables...")
    
    try:
        # Test context processor for categories
        from app import inject_categories
        categories = inject_categories().get('categories', [])
        logger.info(f"Categories from context processor: {len(categories)}")
        for category in categories:
            logger.info(f"   - {category['slug']}: {category['name']} ({category['count']} posts)")
        
        # Test context processor for upload URL
        from app import inject_upload_url
        upload_url = inject_upload_url().get('upload_url', '')
        logger.info(f"Upload URL from context processor: {upload_url}")
    except Exception as e:
        logger.error(f"❌ Error checking template variables: {str(e)}")
        logger.error(traceback.format_exc())

def main():
    """Run all diagnostics"""
    logger.info("Starting diagnostics...")
    
    # Check Flask configuration
    logger.info(f"Flask debug mode: {app.debug}")
    logger.info(f"Flask environment: {os.environ.get('FLASK_ENV', 'Not set')}")
    logger.info(f"Static folder: {app.static_folder}")
    logger.info(f"Template folder: {app.template_folder}")
    
    # Use application context for all Flask operations
    with app.app_context():
        # Run checks
        check_static_files()
        check_template_variables()
        check_database_categories()
        
        # Skip template rendering for now
        # check_template_rendering()
    
    logger.info("Diagnostics complete.")

if __name__ == "__main__":
    main() 