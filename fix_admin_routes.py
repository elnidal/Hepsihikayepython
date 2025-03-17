import os
import sys
import logging
import re
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_admin_templates():
    """Check if all required admin templates exist"""
    logger.info("Checking admin templates...")
    
    required_templates = [
        'templates/admin/base.html',
        'templates/admin/dashboard.html',
        'templates/admin/new_post.html',
        'templates/admin/new_video.html',
        'templates/admin/youtube_sync.html',
        'templates/admin/comments.html',
        'templates/admin/settings.html'
    ]
    
    missing_templates = []
    for template in required_templates:
        if not os.path.exists(template):
            missing_templates.append(template)
            logger.error(f"Missing template: {template}")
    
    if missing_templates:
        logger.error(f"Found {len(missing_templates)} missing templates")
    else:
        logger.info("All required templates exist")
    
    return missing_templates

def fix_admin_routes():
    """Fix issues with admin routes in app.py"""
    logger.info("Starting to fix admin routes in app.py...")
    
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
        with open(f"{app_py_path}.admin.bak", 'w') as f:
            f.write(content)
        logger.info(f"Created backup of app.py at {app_py_path}.admin.bak")
        
        # Look for the admin index route
        admin_route_pattern = r'@app\.route\([\'\"]\/?admin[\'\"]\)[^\n]*\n\s*@login_required[^\n]*\n\s*def admin_index\(\):'
        admin_route_match = re.search(admin_route_pattern, content)
        
        if not admin_route_match:
            logger.error("Could not find admin_index route definition in app.py")
            return False
        
        # Find all error messages returned in admin_index
        error_pattern = r'admin_index.*?return render_template\([\'\"]errors\/\d+\.html[\'\"]\)'
        error_matches = re.findall(error_pattern, content, re.DOTALL)
        
        if error_matches:
            logger.warning(f"Found {len(error_matches)} error returns in admin_index")
        
        # Check for active_page parameter
        active_page_pattern = r'render_template\([\'\"]admin\/dashboard\.html[\'\"],.*?active_page=[\'\"]dashboard[\'\"]'
        active_page_match = re.search(active_page_pattern, content)
        
        if not active_page_match:
            logger.warning("active_page parameter may be missing in admin_index route")
            
            # Try to fix missing active_page parameter
            dashboard_pattern = r'(render_template\([\'\"]admin\/dashboard\.html[\'\"],\s*posts=posts,\s*videos=videos)(\))'
            updated_content = re.sub(dashboard_pattern, r'\1, active_page="dashboard"\2', content)
            
            if updated_content != content:
                logger.info("Added missing active_page parameter to admin_index route")
                content = updated_content
        
        # Check URL_for references
        url_for_pattern = r'url_for\([\'\"](admin_\w+)[\'\"]\)'
        url_for_matches = re.findall(url_for_pattern, content)
        
        # Check function definitions
        function_pattern = r'def\s+(admin_\w+)\('
        function_matches = re.findall(function_pattern, content)
        
        # Find mismatched URL references
        function_names = set(function_matches)
        url_references = set(url_for_matches)
        
        missing_functions = url_references - function_names
        if missing_functions:
            logger.error(f"URL references without matching functions: {missing_functions}")
        
        # Write the updated file if changed
        if content != open(app_py_path, 'r').read():
            with open(app_py_path, 'w') as f:
                f.write(content)
            logger.info("Successfully updated admin routes in app.py")
        else:
            logger.info("No changes needed for admin routes")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing admin routes: {str(e)}")
        return False

def add_debug_logging():
    """Add debug logging to admin routes"""
    logger.info("Adding debug logging to admin routes...")
    
    app_py_path = 'app.py'
    
    try:
        with open(app_py_path, 'r') as f:
            content = f.read()
        
        # Find admin route handlers
        admin_routes = re.findall(r'@app\.route\([\'\"]\/?admin.*?\n\s*@login_required.*?\n\s*def (admin_\w+)\(', content, re.DOTALL)
        
        logger.info(f"Found {len(admin_routes)} admin route handlers")
        
        # Add debug logging to each admin route
        for route in admin_routes:
            route_pattern = rf'def {route}\([^)]*\):\s*\"\"\"[^\"]*\"\"\"\s*'
            debug_log = f'def {route}(\\1):\\n    """\\2"""\\n    app.logger.debug(f"Entering {route} route")\\n    '
            
            content = re.sub(route_pattern, debug_log, content)
        
        # Write the updated file
        with open(app_py_path, 'w') as f:
            f.write(content)
        
        logger.info("Successfully added debug logging to admin routes")
        return True
        
    except Exception as e:
        logger.error(f"Error adding debug logging: {str(e)}")
        return False

def create_error_log_viewer():
    """Create a temporary error log viewer script"""
    logger.info("Creating error log viewer script...")
    
    script_content = """import os
import sys
import re
from datetime import datetime, timedelta

def read_error_logs():
    # Define common log file locations
    possible_log_files = [
        'app.log',
        'error.log',
        'flask.log',
        '/var/log/nginx/error.log',
        '/var/log/apache2/error.log',
        os.path.join('logs', 'app.log'),
        os.path.join('log', 'app.log')
    ]
    
    # Check if running on Render.com
    if os.environ.get('RENDER'):
        render_log_dir = '/var/log/app'
        if os.path.isdir(render_log_dir):
            for filename in os.listdir(render_log_dir):
                if filename.endswith('.log'):
                    possible_log_files.append(os.path.join(render_log_dir, filename))
    
    errors = []
    
    # Time threshold - last 24 hours
    time_threshold = datetime.now() - timedelta(hours=24)
    
    # Regular expressions for different log formats
    error_patterns = [
        r'.*ERROR.*',  # Standard ERROR level
        r'.*Error.*',  # Error message
        r'.*Exception.*',  # Exceptions
        r'.*HTTP.*(500|502|503|504).*',  # HTTP error status codes
        r'.*Traceback.*'  # Python tracebacks
    ]
    compiled_patterns = [re.compile(pattern) for pattern in error_patterns]
    
    for log_file in possible_log_files:
        if os.path.isfile(log_file):
            print(f"Reading log file: {log_file}")
            try:
                with open(log_file, 'r', errors='ignore') as f:
                    lines = f.readlines()
                    
                    # Process the log file
                    current_error = []
                    in_error = False
                    
                    for line in lines:
                        # Check if line matches any error pattern
                        is_error_line = any(pattern.match(line) for pattern in compiled_patterns)
                        
                        # If we find an error line
                        if is_error_line:
                            if not in_error:
                                in_error = True
                                current_error = [line]
                            else:
                                current_error.append(line)
                        # If we're in an error block but this line isn't an error
                        elif in_error:
                            # If line starts with whitespace, it's likely part of a traceback
                            if line.startswith(' ') or line.startswith('\\t'):
                                current_error.append(line)
                            else:
                                # End of error block
                                errors.append(''.join(current_error))
                                in_error = False
                                current_error = []
                    
                    # Add the last error if we're still processing one
                    if in_error and current_error:
                        errors.append(''.join(current_error))
                        
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
    
    # Sort errors by timestamp if available
    return errors

if __name__ == '__main__':
    errors = read_error_logs()
    
    print(f"Found {len(errors)} error entries in logs")
    
    if errors:
        print("\\nLatest errors (most recent first):\\n")
        # Print the 10 most recent errors
        for i, error in enumerate(errors[-10:], 1):
            print(f"--- Error {i} ---")
            print(error)
            print()
    
    # If admin routes are mentioned in errors, highlight them
    admin_errors = [error for error in errors if 'admin' in error.lower()]
    if admin_errors:
        print(f"\\nFound {len(admin_errors)} errors related to admin routes:\\n")
        for i, error in enumerate(admin_errors[-5:], 1):
            print(f"--- Admin Error {i} ---")
            print(error)
            print()
"""
    
    with open('view_error_logs.py', 'w') as f:
        f.write(script_content)
    
    logger.info("Created error log viewer script: view_error_logs.py")
    return True

if __name__ == "__main__":
    # Check admin templates
    missing_templates = check_admin_templates()
    
    # Fix admin routes if needed
    fix_admin_routes()
    
    # Add debug logging to admin routes
    add_debug_logging()
    
    # Create error log viewer script
    create_error_log_viewer()
    
    logger.info("Admin route checks and fixes completed")
    
    # Print a reminder about running in debug mode
    print("\nReminder: To troubleshoot the admin panel issue, try running the Flask app in debug mode:")
    print("export FLASK_DEBUG=1")
    print("flask run\n")
    
    print("Then check the error logs with:")
    print("python view_error_logs.py") 