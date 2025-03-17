import os
import re
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def fix_serve_upload_function():
    """Fix the serve_upload function in app.py to better handle missing files"""
    logger.info("Starting to fix the serve_upload function in app.py...")
    
    app_py_path = 'app.py'
    
    # Check if app.py exists
    if not os.path.isfile(app_py_path):
        logger.error(f"app.py file not found at {app_py_path}")
        return False
    
    # Read the app.py file
    try:
        with open(app_py_path, 'r') as f:
            content = f.read()
        
        # Make a backup
        with open(f"{app_py_path}.bak", 'w') as f:
            f.write(content)
        logger.info(f"Created backup of app.py at {app_py_path}.bak")
        
        # Find the serve_upload function
        route_pattern = r'@app\.route\([\'\"]\/uploads\/<path:filename>[\'\"]\)[^\n]*\n\s*def serve_upload\(filename\):'
        route_match = re.search(route_pattern, content)
        
        if not route_match:
            logger.error("Could not find serve_upload route definition in app.py")
            return False
        
        route_start = route_match.start()
        func_start = content.find("def serve_upload(filename):", route_start)
        
        # Find function end 
        # (looking for the next def, route decorator, or empty line)
        func_end = -1
        lines = content[func_start:].split('\n')
        indent_level = len(lines[0]) - len(lines[0].lstrip())
        line_count = 1
        
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '':
                continue
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= indent_level and (line.lstrip().startswith('def ') or line.lstrip().startswith('@')):
                func_end = func_start + sum(len(l) + 1 for l in lines[:i])
                break
            line_count += 1
        
        if func_end == -1:
            # If we can't find end, estimate it
            func_end = func_start + sum(len(l) + 1 for l in lines[:line_count])
        
        # Replace the function with improved version
        improved_function = """@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    \"\"\"Serve uploaded files from the static/uploads directory\"\"\"
    try:
        # Check if file exists in static/uploads
        upload_path = os.path.join(app.static_folder, 'uploads', filename)
        if os.path.isfile(upload_path):
            return redirect(url_for('static', filename=f'uploads/{filename}'))
        else:
            app.logger.warning(f"File not found: {upload_path}")
            # Return default image
            return redirect(url_for('static', filename='uploads/default_post_image.png'))
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {str(e)}")
        # Return a default image if there's any error
        return redirect(url_for('static', filename='uploads/default_post_image.png'))"""
        
        # Replace the old function with the improved one
        new_content = content[:route_start] + improved_function + content[func_end:]
        
        # Check if we need to add import for os
        if "import os" not in new_content:
            # Find the import block
            import_match = re.search(r'import\s+[^\n]+', new_content)
            if import_match:
                import_end = import_match.end()
                new_content = new_content[:import_end] + "\nimport os" + new_content[import_end:]
            else:
                logger.warning("Could not find a suitable place to add 'import os'. Adding at the beginning.")
                new_content = "import os\n" + new_content
        
        # Write the updated file
        with open(app_py_path, 'w') as f:
            f.write(new_content)
        
        logger.info("Successfully updated the serve_upload function in app.py")
        return True
        
    except Exception as e:
        logger.error(f"Error updating serve_upload function: {str(e)}")
        return False

if __name__ == "__main__":
    fix_serve_upload_function() 