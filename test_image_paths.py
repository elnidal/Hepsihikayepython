#!/usr/bin/env python
"""
Test script to verify image path handling configuration
This won't modify any real data but will show you how paths will be handled
"""
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('image_test')

# Add a file handler to save logs
file_handler = logging.FileHandler('image_test.log')
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

def test_image_paths():
    """Test how image paths will be handled in different environments"""
    # Simulate both environments
    environments = ['development', 'production']
    
    for env in environments:
        logger.info(f"\n{'='*50}\nTesting in {env.upper()} environment\n{'='*50}")
        
        # Set environment variable to simulate the environment
        is_production = (env == 'production')
        
        # Simulate app configuration
        app_config = {}
        static_folder = 'static'
        
        # Configure upload folder based on environment
        if is_production:
            app_config['UPLOAD_FOLDER'] = '/opt/render/project/src/uploads'
            app_config['UPLOAD_URL'] = '/uploads'
        else:
            app_config['UPLOAD_FOLDER'] = os.path.join(static_folder, 'uploads')
            app_config['UPLOAD_URL'] = '/static/uploads'
        
        # Normalize paths
        app_config['UPLOAD_FOLDER'] = app_config['UPLOAD_FOLDER'].rstrip('/')
        app_config['UPLOAD_URL'] = app_config['UPLOAD_URL'].rstrip('/')
        app_config['IS_PRODUCTION'] = is_production
        
        # Log environment-specific settings
        logger.info(f"Environment: {env}")
        logger.info(f"Upload folder: {app_config['UPLOAD_FOLDER']}")
        logger.info(f"Upload URL path: {app_config['UPLOAD_URL']}")
        
        # Test file paths for common scenarios
        test_filenames = [
            'test.jpg',
            'file with spaces.png',
            'path/to/nested/image.jpg',
            '/absolute/path/image.gif'
        ]
        
        for filename in test_filenames:
            # Normalize filename - strip leading slash
            normalized = filename.lstrip('/')
            
            # Calculate storage path
            storage_path = os.path.join(app_config['UPLOAD_FOLDER'], normalized)
            
            # Calculate URL
            if is_production:
                url = f"/uploads/{normalized}"
            else:
                url = f"/static/uploads/{normalized}"
            
            logger.info(f"\nFilename: {filename}")
            logger.info(f"Normalized: {normalized}")
            logger.info(f"Storage path: {storage_path}")
            logger.info(f"URL: {url}")
            
            # Show how file would be served
            if is_production:
                serve_dir = app_config['UPLOAD_FOLDER']
                serve_file = normalized
            else:
                serve_dir = os.path.join(static_folder, 'uploads')
                serve_file = normalized
            
            logger.info(f"Would serve from: {serve_dir} as {serve_file}")

if __name__ == "__main__":
    print("Running image path handling test...")
    test_image_paths()
    print("Test complete! Check image_test.log for detailed results.") 