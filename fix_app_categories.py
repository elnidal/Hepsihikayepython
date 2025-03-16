#!/usr/bin/env python3
import os
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_inject_categories():
    """Fix the inject_categories function to always show all categories"""
    try:
        app_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
        
        with open(app_py_path, 'r') as file:
            content = file.read()
        
        # Find the inject_categories function
        inject_categories_pattern = r'@app\.context_processor\s*\ndef\s+inject_categories\(\):'
        match = re.search(inject_categories_pattern, content)
        
        if not match:
            logger.error("Could not find inject_categories function in app.py")
            return False
        
        # Find the start of the function
        func_start = match.start()
        
        # Find the end of the function (next function or route)
        next_func_pattern = r'(@app\.|def\s+\w+\()'
        next_match = re.search(next_func_pattern, content[func_start + 20:])
        
        if not next_match:
            logger.error("Could not find the end of inject_categories function")
            return False
            
        func_end = func_start + 20 + next_match.start()
        
        # Extract the current function
        current_func = content[func_start:func_end]
        logger.info(f"Found inject_categories function at position {func_start}-{func_end}")
        
        # Check if it already shows all categories
        if "# Always include all defined categories" in current_func:
            logger.info("inject_categories function already shows all categories")
            return True
        
        # Create the new function that always shows all categories
        new_func = """@app.context_processor
def inject_categories():
    \"\"\"Make categories available to all templates\"\"\"
    try:
        app.logger.info("Injecting categories for template")
        
        # Get all defined categories from the global CATEGORIES list
        all_categories = []
        category_dict = dict(CATEGORIES)
        
        # Always include all defined categories, even if they have no posts
        for cat_key, cat_name in CATEGORIES:
            count = 0
            try:
                # Check if there are posts in this category
                count = Post.query.filter_by(category=cat_key).count()
            except Exception as e:
                # If there's a database error, just use 0
                app.logger.error(f"Error counting posts for category {cat_key}: {str(e)}")
                pass
                
            all_categories.append({
                'slug': cat_key,
                'name': cat_name,
                'count': count
            })
                
        app.logger.info(f"Returning {len(all_categories)} categories to template")
        return {'categories': all_categories}
        
    except Exception as e:
        # Log any other errors but don't crash - return empty categories
        app.logger.error(f"Unexpected error injecting categories: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Always return a valid list, even if empty
        return {'categories': []}
"""
        
        # Replace the function in the content
        modified_content = content[:func_start] + new_func + content[func_end:]
        
        # Write the modified content back to app.py
        with open(app_py_path, 'w') as file:
            file.write(modified_content)
            
        logger.info("Successfully updated inject_categories function to show all categories")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing inject_categories: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fix_serve_upload_route():
    """Fix the serve_upload route to use static files"""
    try:
        app_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
        
        with open(app_py_path, 'r') as file:
            content = file.read()
        
        # Find the serve_upload route
        serve_upload_pattern = r'@app\.route\(\s*[\'\"]\/uploads\/\<path:filename\>[\'\"]\s*\)\s*\ndef\s+serve_upload\(\s*filename\s*\):'
        match = re.search(serve_upload_pattern, content)
        
        if not match:
            logger.error("Could not find serve_upload route in app.py")
            return False
        
        # Find the start of the function
        func_start = match.start()
        
        # Find the end of the function (next function or route)
        next_func_pattern = r'(@app\.|def\s+\w+\()'
        next_match = re.search(next_func_pattern, content[func_start + 20:])
        
        if not next_match:
            logger.error("Could not find the end of serve_upload function")
            return False
            
        func_end = func_start + 20 + next_match.start()
        
        # Extract the current function
        current_func = content[func_start:func_end]
        logger.info(f"Found serve_upload function at position {func_start}-{func_end}")
        
        # Check if it already uses static files
        if "return redirect(url_for('static', filename=" in current_func:
            logger.info("serve_upload route already uses static files")
            return True
        
        # Create the new function that uses static files
        new_func = """@app.route('/uploads/<path:filename>')
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
        
        # Replace the function in the content
        modified_content = content[:func_start] + new_func + content[func_end:]
        
        # Write the modified content back to app.py
        with open(app_py_path, 'w') as file:
            file.write(modified_content)
            
        logger.info("Successfully updated serve_upload route to use static files")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing serve_upload route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fix_get_image_url_method():
    """Fix the get_image_url method in the Post model"""
    try:
        app_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
        
        with open(app_py_path, 'r') as file:
            content = file.read()
        
        # Find the get_image_url method
        get_image_url_pattern = r'def\s+get_image_url\(\s*self\s*\):'
        match = re.search(get_image_url_pattern, content)
        
        if not match:
            logger.error("Could not find get_image_url method in app.py")
            return False
        
        # Find the start of the method
        method_start = match.start()
        
        # Find the end of the method (next method or function)
        next_method_pattern = r'def\s+\w+\('
        next_match = re.search(next_method_pattern, content[method_start + 20:])
        
        if not next_match:
            logger.error("Could not find the end of get_image_url method")
            return False
            
        method_end = method_start + 20 + next_match.start()
        
        # Extract the current method
        current_method = content[method_start:method_end]
        logger.info(f"Found get_image_url method at position {method_start}-{method_end}")
        
        # Check if it already uses static files
        if "return url_for('static', filename=" in current_method:
            logger.info("get_image_url method already uses static files")
            return True
        
        # Create the new method that uses static files
        new_method = """def get_image_url(self):
        \"\"\"Get the full URL for the post image\"\"\"
        if not self.image_url:
            return url_for('static', filename='uploads/default_post_image.png')
        
        # Check if the image_url already has the correct format
        if self.image_url.startswith('uploads/'):
            return url_for('static', filename=self.image_url)
        else:
            # Otherwise, prepend the uploads/ directory
            return url_for('static', filename=f'uploads/{self.image_url}')

    """
        
        # Replace the method in the content
        modified_content = content[:method_start] + new_method + content[method_end:]
        
        # Write the modified content back to app.py
        with open(app_py_path, 'w') as file:
            file.write(modified_content)
            
        logger.info("Successfully updated get_image_url method to use static files")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing get_image_url method: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all fixes"""
    logger.info("Starting to fix app.py...")
    
    # Step 1: Fix inject_categories function
    if fix_inject_categories():
        logger.info("✅ Successfully fixed inject_categories function")
    else:
        logger.error("❌ Failed to fix inject_categories function")
    
    # Step 2: Fix serve_upload route
    if fix_serve_upload_route():
        logger.info("✅ Successfully fixed serve_upload route")
    else:
        logger.error("❌ Failed to fix serve_upload route")
    
    # Step 3: Fix get_image_url method
    if fix_get_image_url_method():
        logger.info("✅ Successfully fixed get_image_url method")
    else:
        logger.error("❌ Failed to fix get_image_url method")
    
    logger.info("All fixes completed")
    
if __name__ == "__main__":
    main() 