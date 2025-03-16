import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import traceback
from flask import Flask, request, got_request_exception
from werkzeug.exceptions import HTTPException

# Import the app and initialize it
from app import app

# Set up enhanced logging
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler('logs/debug.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.DEBUG)

# Add stream handler for console output
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
stream_handler.setLevel(logging.DEBUG)

# Remove existing handlers to avoid duplicates
for handler in app.logger.handlers[:]:
    app.logger.removeHandler(handler)

app.logger.addHandler(file_handler)
app.logger.addHandler(stream_handler)
app.logger.setLevel(logging.DEBUG)
app.logger.info('Debug server starting...')

# Log request details
@app.before_request
def log_request_info():
    app.logger.debug('Request: %s %s', request.method, request.path)
    app.logger.debug('Headers: %s', dict(request.headers))
    app.logger.debug('Body: %s', request.get_data())

# Log exceptions
def log_exception(sender, exception):
    tb = traceback.format_exc()
    app.logger.error(f'Exception on {request.path} [{request.method}]: {str(exception)}\n{tb}')

got_request_exception.connect(log_exception, app)

# Custom error handlers for better debugging
@app.errorhandler(404)
def not_found_error(error):
    app.logger.warning(f'404 Error: {request.path}')
    return app.send_static_file('404.html') if os.path.exists(app.static_folder + '/404.html') else 'Page not found', 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'500 Error: {request.path}')
    # Log the type of exception and traceback
    if isinstance(error, Exception):
        app.logger.error(f'Exception type: {type(error).__name__}')
        app.logger.error(f'Exception message: {str(error)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
    return app.send_static_file('500.html') if os.path.exists(app.static_folder + '/500.html') else 'Server error', 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Handle HTTP exceptions
    if isinstance(e, HTTPException):
        return e
    
    # Log the exception with detailed information
    app.logger.error(f'Unhandled Exception: {str(e)}')
    app.logger.error(f'Exception type: {type(e).__name__}')
    app.logger.error(f'Traceback: {traceback.format_exc()}')
    return 'Server Error', 500

# Run the server with debugging enabled
if __name__ == '__main__':
    # Initialize the app
    if hasattr(app, 'init_app'):
        app.init_app()
    
    # Choose a different port to avoid conflicts
    port = int(os.environ.get('PORT', 10002))
    app.logger.info(f'Starting debug server on port {port}')
    app.run(debug=True, host='0.0.0.0', port=port) 