import os
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
                            if line.startswith(' ') or line.startswith('\t'):
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
        print("\nLatest errors (most recent first):\n")
        # Print the 10 most recent errors
        for i, error in enumerate(errors[-10:], 1):
            print(f"--- Error {i} ---")
            print(error)
            print()
    
    # If admin routes are mentioned in errors, highlight them
    admin_errors = [error for error in errors if 'admin' in error.lower()]
    if admin_errors:
        print(f"\nFound {len(admin_errors)} errors related to admin routes:\n")
        for i, error in enumerate(admin_errors[-5:], 1):
            print(f"--- Admin Error {i} ---")
            print(error)
            print()
