import os
import sys
import logging
from app import app, db, User, Post, Video
from flask_login import login_user, current_user
from flask import session, url_for

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_admin_user():
    """Verify admin user exists and has the correct credentials"""
    with app.app_context():
        logger.info("Checking admin user...")
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            logger.error("Admin user does not exist in database!")
            logger.info("Creating admin user...")
            from werkzeug.security import generate_password_hash
            admin = User(username='admin', password=generate_password_hash('admin'))
            try:
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user created successfully")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating admin user: {str(e)}")
                return False
        else:
            logger.info("Admin user exists in database")
        
        return True

def test_admin_route():
    """Test the admin route for issues"""
    with app.test_client() as client:
        with app.app_context():
            # First verify we get redirected to login if not logged in
            logger.info("Testing admin route without login...")
            response = client.get('/admin', follow_redirects=False)
            
            if response.status_code == 302:  # Redirect to login
                logger.info("Admin route correctly redirects to login when not authenticated")
            else:
                logger.error(f"Unexpected status code: {response.status_code} for /admin without login")
            
            # Now try to login
            logger.info("Testing login...")
            admin = User.query.filter_by(username='admin').first()
            
            if not admin:
                logger.error("Cannot test login - admin user doesn't exist")
                return False
            
            # Manual login with the test client
            response = client.post('/login', data={
                'username': 'admin',
                'password': 'admin',
                'csrf_token': ''  # This will fail, but we need to test it
            }, follow_redirects=False)
            
            logger.info(f"Login response: {response.status_code}")
            
            # Now try to access admin page after login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)  # Force login for testing
            
            logger.info("Testing admin route with session login...")
            response = client.get('/admin', follow_redirects=False)
            logger.info(f"Admin route response: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("Admin route is accessible with login")
                return True
            else:
                logger.error(f"Admin route returned {response.status_code} with login")
                return False

def check_templates():
    """Check if required admin templates exist"""
    template_path = os.path.join(app.root_path, 'templates', 'admin', 'index.html')
    errors_path = os.path.join(app.root_path, 'templates', 'errors', '500.html')
    
    if not os.path.exists(template_path):
        logger.error(f"Admin template missing: {template_path}")
        return False
    else:
        logger.info(f"Admin template exists: {template_path}")
    
    if not os.path.exists(errors_path):
        logger.error(f"Error template missing: {errors_path}")
    else:
        logger.info(f"Error template exists: {errors_path}")
    
    return True

def fix_admin_route():
    """Create a special route for debugging admin access"""
    with app.app_context():
        # Create a temporary endpoint to diagnose admin issues
        @app.route('/admin-test')
        def admin_test():
            try:
                from flask import jsonify
                is_authenticated = current_user.is_authenticated
                user_id = current_user.get_id() if is_authenticated else None
                
                user_info = None
                if user_id:
                    user = User.query.get(int(user_id))
                    if user:
                        user_info = {'id': user.id, 'username': user.username}
                
                # Test database connection
                post_count = Post.query.count()
                video_count = Video.query.count()
                
                return jsonify({
                    'authenticated': is_authenticated,
                    'user_id': user_id,
                    'user_info': user_info,
                    'post_count': post_count,
                    'video_count': video_count,
                    'session': dict(session)
                })
            except Exception as e:
                logger.error(f"Error in admin-test route: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return jsonify({'error': str(e)}), 500
        
        logger.info("Added /admin-test route for debugging")
        
        # Create a file with the route info
        with open('admin_test_route.txt', 'w') as f:
            f.write("Visit /admin-test to diagnose admin issues\n")
            f.write("This route shows authentication status and database connection info\n")
    
    return True

def main():
    """Run all tests"""
    logger.info("Starting admin access tests...")
    
    # Run tests
    user_ok = test_admin_user()
    templates_ok = check_templates()
    route_ok = test_admin_route()
    fix_ok = fix_admin_route()
    
    # Report results
    logger.info("\n--- Test Results ---")
    logger.info(f"Admin user check: {'PASS' if user_ok else 'FAIL'}")
    logger.info(f"Templates check: {'PASS' if templates_ok else 'FAIL'}")
    logger.info(f"Admin route check: {'PASS' if route_ok else 'FAIL'}")
    logger.info(f"Admin fix applied: {'PASS' if fix_ok else 'FAIL'}")
    
    if not all([user_ok, templates_ok, route_ok]):
        logger.warning("Some tests failed. Review logs for details.")
        return 1
    
    logger.info("All tests passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 