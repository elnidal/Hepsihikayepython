import os
import sys
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_admin_login():
    """Fix the admin login by ensuring the user exists and resetting the password"""
    try:
        # Import app and db from the main application
        from app import app, db, User
        
        with app.app_context():
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            
            if admin:
                logger.info("Admin user exists, updating password")
                admin.password = generate_password_hash('admin')
                db.session.commit()
                logger.info("Admin password updated successfully")
            else:
                logger.info("Admin user does not exist, creating new user")
                # Create admin user
                admin = User(username='admin', password=generate_password_hash('admin'))
                db.session.add(admin)
                db.session.commit()
                logger.info("Admin user created successfully")
            
            logger.info(f"Admin user id: {admin.id}")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing admin login: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def create_simple_admin_route():
    """Create a simplified version of the admin route to diagnose issues"""
    try:
        # Import necessary modules
        from app import app, db
        
        # Add a simpler admin route without any database queries
        with open('simple_admin.py', 'w') as f:
            f.write("""from app import app
from flask import render_template
from flask_login import login_required

@app.route('/admin-simple')
@login_required
def admin_simple():
    return render_template('simple_post.html', title='Admin Simple', content='Admin page is working!')
""")
        
        logger.info("Created simplified admin route at /admin-simple")
        logger.info("Run 'python -c \"import simple_admin\"' before starting the app to register the route")
        return True
        
    except Exception as e:
        logger.error(f"Error creating simplified admin route: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def create_error_template():
    """Create a simple error template if it doesn't exist"""
    try:
        from app import app
        
        # Create templates/errors directory if it doesn't exist
        errors_dir = os.path.join(app.root_path, 'templates', 'errors')
        os.makedirs(errors_dir, exist_ok=True)
        
        # Create 500.html if it doesn't exist
        error_template = os.path.join(errors_dir, '500.html')
        if not os.path.exists(error_template):
            with open(error_template, 'w') as f:
                f.write("""{% extends "base.html" %}

{% block content %}
<div class="container">
    <div class="row">
        <div class="col-md-12 text-center">
            <h1 class="mt-5 text-danger">Sunucu Hatası</h1>
            <div class="alert alert-danger mt-4">
                <h2>Üzgünüz, bir sorun oluştu</h2>
                <p>Sunucu beklenmedik bir hata ile karşılaştı ve isteğinizi şu anda işleyemiyor.</p>
            </div>
            <p class="mt-4">
                <a href="{{ url_for('index') }}" class="btn btn-primary">Ana Sayfaya Dön</a>
            </p>
        </div>
    </div>
</div>
{% endblock %}""")
            logger.info(f"Created error template: {error_template}")
        else:
            logger.info(f"Error template already exists: {error_template}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating error template: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def create_simple_template():
    """Create a simple template for testing admin routes"""
    try:
        from app import app
        
        # Create simple_post.html template
        template_path = os.path.join(app.root_path, 'templates', 'simple_post.html')
        if not os.path.exists(template_path):
            with open(template_path, 'w') as f:
                f.write("""{% extends "base.html" %}

{% block content %}
<div class="container">
    <div class="row">
        <div class="col-md-12">
            <h1>{{ title }}</h1>
            <div class="card">
                <div class="card-body">
                    {{ content|safe }}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")
            logger.info(f"Created simple template: {template_path}")
        else:
            logger.info(f"Simple template already exists: {template_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating simple template: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def fix_admin_index():
    """Fix the admin/index.html template if it has issues"""
    try:
        from app import app
        
        template_path = os.path.join(app.root_path, 'templates', 'admin', 'index.html')
        
        # Create backup of the current template
        if os.path.exists(template_path):
            import shutil
            backup_path = template_path + '.bak'
            shutil.copy2(template_path, backup_path)
            logger.info(f"Backed up admin template to: {backup_path}")
        
        # Create a simplified index.html for testing
        with open(template_path, 'w') as f:
            f.write("""{% extends "base.html" %}

{% block content %}
<div class="container">
    <div class="row">
        <div class="col-md-12">
            <h1>Admin Panel</h1>
            <div class="alert alert-success">
                <p>Admin panel is working correctly.</p>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    <h2>Posts</h2>
                </div>
                <div class="card-body">
                    {% if posts %}
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Title</th>
                                    <th>Category</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for post in posts %}
                                <tr>
                                    <td>{{ post.id }}</td>
                                    <td>{{ post.title }}</td>
                                    <td>{{ post.category }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p>No posts found.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")
        logger.info(f"Updated admin template: {template_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error fixing admin index template: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all fixes"""
    logger.info("Starting admin route fixes...")
    
    # Run fixes
    login_fix = fix_admin_login()
    template_fix = create_simple_template()
    error_fix = create_error_template()
    admin_fix = fix_admin_index()
    route_fix = create_simple_admin_route()
    
    # Report results
    logger.info("\n--- Fix Results ---")
    logger.info(f"Admin login fix: {'PASS' if login_fix else 'FAIL'}")
    logger.info(f"Template creation: {'PASS' if template_fix else 'FAIL'}")
    logger.info(f"Error template fix: {'PASS' if error_fix else 'FAIL'}")
    logger.info(f"Admin index fix: {'PASS' if admin_fix else 'FAIL'}")
    logger.info(f"Simple route creation: {'PASS' if route_fix else 'FAIL'}")
    
    if all([login_fix, template_fix, error_fix, admin_fix, route_fix]):
        logger.info("\nAll fixes were applied successfully!")
        logger.info("\nTo activate the simple admin route:")
        logger.info("1. Run: python -c \"import simple_admin\"")
        logger.info("2. Restart your Flask application")
        logger.info("3. Visit: /admin-simple to test admin access")
        logger.info("\nAdmin credentials: admin / admin")
        return 0
    else:
        logger.warning("\nSome fixes failed. Review logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 