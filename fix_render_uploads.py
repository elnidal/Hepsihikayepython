#!/usr/bin/env python3
import os
import logging
from app import app, db, Post

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_image_paths():
    """Update the paths of images in posts to use a persistent storage solution"""
    try:
        with app.app_context():
            # Get all posts with images
            posts_with_images = Post.query.filter(Post.image_url != None, Post.image_url != '').all()
            logger.info(f"Found {len(posts_with_images)} posts with images")
            
            for post in posts_with_images:
                original_image = post.image_url
                logger.info(f"Checking post ID {post.id} with image: {original_image}")
                
                # Extract just the filename from the path, in case it includes directory info
                filename = os.path.basename(original_image)
                
                # For Render.com deployment, we should ensure images are in the static/uploads folder
                # which is part of the git repository and will be deployed
                if '/uploads/' not in post.image_url and filename:
                    # Update to point to the static/uploads directory
                    post.image_url = f"uploads/{filename}"
                    logger.info(f"Updated post ID {post.id} image from '{original_image}' to '{post.image_url}'")
                
            # Commit all changes
            db.session.commit()
            logger.info("All post image paths updated successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error updating image paths: {str(e)}")
        if 'db' in locals() and db.session:
            db.session.rollback()
        return False

def ensure_uploads_directory():
    """Ensure the uploads directory exists and is correctly configured"""
    try:
        # Check if we're in production (Render.com)
        is_production = os.environ.get('FLASK_ENV') == 'production'
        
        if is_production:
            # For Render.com, we need to use the /opt/render/project/src/static/uploads directory
            upload_dir = '/opt/render/project/src/static/uploads'
        else:
            # For local development
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        
        # Create directory if it doesn't exist
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            logger.info(f"Created uploads directory at: {upload_dir}")
        else:
            logger.info(f"Uploads directory already exists at: {upload_dir}")
            
        # Update app configuration
        with open('app.py', 'r') as file:
            content = file.read()
            
        # Look for the upload directory configuration
        if "UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')" in content:
            # Replace with the correct path
            modified_content = content.replace(
                "UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')",
                "UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')"
            )
            
            # Also update any other references to 'uploads' path
            modified_content = modified_content.replace("url_for('serve_file', filename=", "url_for('static', filename='uploads/")
            
            with open('app.py', 'w') as file:
                file.write(modified_content)
                
            logger.info("Updated app.py to use static/uploads directory")
        else:
            logger.info("Upload folder already seems to be correctly configured")
            
        return True
            
    except Exception as e:
        logger.error(f"Error ensuring uploads directory: {str(e)}")
        return False

def create_uploads_readme():
    """Create a readme file in the uploads directory to ensure it's included in Git"""
    try:
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'README.md')
        with open(readme_path, 'w') as file:
            file.write("""# Uploads Directory

This directory is used for storing uploaded files for the HepsiHikaye website.

## Important Note

When deploying to Render.com:
1. This directory is included in the Git repository to ensure it exists in the deployment.
2. Any files uploaded in production will NOT persist between deployments because Render uses an ephemeral filesystem.
3. For production use, consider using a cloud storage service like AWS S3.

## Default Images

Place default images in this directory to ensure they're available in production.
""")
        logger.info(f"Created README.md in uploads directory at: {readme_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating uploads readme: {str(e)}")
        return False

def fix_serve_upload_route():
    """Fix the serve_upload route to use static files"""
    try:
        with open('app.py', 'r') as file:
            content = file.read()
            
        # Check if we need to update the serve_upload route
        if "@app.route('/uploads/<path:filename>')" in content and "def serve_upload(filename):" in content:
            # Find the route definition
            route_start = content.find("@app.route('/uploads/<path:filename>')")
            if route_start == -1:
                logger.error("Could not find serve_upload route in app.py")
                return False
                
            # Find the function definition
            func_start = content.find("def serve_upload(filename):", route_start)
            if func_start == -1:
                logger.error("Could not find serve_upload function in app.py")
                return False
                
            # Find the end of the function
            next_def = content.find("@app.route", func_start)
            if next_def == -1:
                next_def = content.find("def ", func_start + 20)
                
            if next_def == -1:
                logger.error("Could not find the end of serve_upload function in app.py")
                return False
                
            # Replace the function with a new implementation that uses static files
            modified_content = content[:route_start]
            modified_content += """@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    \"\"\"Serve uploaded files from the static/uploads directory\"\"\"
    try:
        # In production, serve from static/uploads
        return redirect(url_for('static', filename=f'uploads/{filename}'))
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {str(e)}")
        # Return a default image if the file doesn't exist
        return redirect(url_for('static', filename='uploads/default_post_image.png'))
"""
            modified_content += content[next_def:]
            
            with open('app.py', 'w') as file:
                file.write(modified_content)
                
            logger.info("Updated serve_upload route to use static files")
            return True
        else:
            logger.info("serve_upload route already seems to be correctly configured")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing serve_upload route: {str(e)}")
        return False

def main():
    """Run all fixes"""
    logger.info("Starting to fix uploads handling for Render.com deployment...")
    
    # Step 1: Ensure the uploads directory exists in the correct location
    if ensure_uploads_directory():
        logger.info("✅ Successfully configured uploads directory")
    else:
        logger.error("❌ Failed to configure uploads directory")
    
    # Step 2: Update image paths in the database
    if update_image_paths():
        logger.info("✅ Successfully updated image paths in database")
    else:
        logger.error("❌ Failed to update image paths in database")
    
    # Step 3: Create a readme to ensure the directory is included in Git
    if create_uploads_readme():
        logger.info("✅ Successfully created uploads README")
    else:
        logger.error("❌ Failed to create uploads README")
        
    # Step 4: Fix the serve_upload route
    if fix_serve_upload_route():
        logger.info("✅ Successfully fixed serve_upload route")
    else:
        logger.error("❌ Failed to fix serve_upload route")
    
    logger.info("All fixes completed")
    
if __name__ == "__main__":
    main() 