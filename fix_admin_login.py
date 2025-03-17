import os
import sys
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def fix_login_required_decorator():
    """Fix any issues with the login_required decorator"""
    logger.info("Checking login_required decorator...")
    
    app_py_path = 'app.py'
    
    try:
        with open(app_py_path, 'r') as f:
            content = f.read()
            
        # Check if login_required is defined
        login_required_pattern = r'def\s+login_required\s*\('
        login_required_match = re.search(login_required_pattern, content)
        
        if not login_required_match:
            logger.warning("login_required decorator might not be defined properly")
            
            # Add a robust login_required decorator if missing
            add_login_decorator = """
# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            app.logger.warning(f"Unauthenticated user attempted to access {request.path}")
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
"""
            # Check if we need to import wraps
            if "from functools import wraps" not in content:
                add_login_decorator = "from functools import wraps\n" + add_login_decorator
            
            # Find a good place to add the decorator
            import_section_end = content.find("app = Flask(__name__)")
            if import_section_end > 0:
                updated_content = content[:import_section_end] + add_login_decorator + content[import_section_end:]
                
                with open(app_py_path, 'w') as f:
                    f.write(updated_content)
                
                logger.info("Added robust login_required decorator")
                return True
            else:
                logger.error("Could not find a suitable place to add login_required decorator")
                return False
        else:
            logger.info("login_required decorator is defined")
            return True
    
    except Exception as e:
        logger.error(f"Error fixing login_required decorator: {str(e)}")
        return False

def fix_admin_login_route():
    """Fix the admin login route"""
    logger.info("Checking admin login route...")
    
    app_py_path = 'app.py'
    
    try:
        with open(app_py_path, 'r') as f:
            content = f.read()
        
        # Check for login route
        login_route_pattern = r'@app\.route\([\'\"]/login[\'\"](,\s*methods=\[[\'\"](GET|POST)[\'\"](,\s*[\'\"](GET|POST)[\'\"])?\])?\)[^\n]*\n\s*def\s+login\(\):'
        login_route_match = re.search(login_route_pattern, content)
        
        if not login_route_match:
            logger.warning("Login route might not be properly defined")
            
            # Add a robust login route
            login_route = """
@app.route('/login', methods=['GET', 'POST'])
def login():
    \"\"\"Handle user login\"\"\"
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('admin_index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # Check if username exists and password is correct
        app.logger.info(f"Login attempt for username: {username}")
        
        try:
            if username == app.config.get('ADMIN_USERNAME') and check_password_hash(app.config.get('ADMIN_PASSWORD_HASH'), password):
                user = User(id=1, username=username)
                login_user(user)
                app.logger.info(f"Successful login for username: {username}")
                
                # Get the page the user tried to access
                next_page = request.args.get('next')
                if not next_page or url_parse(next_page).netloc != '':
                    next_page = url_for('admin_index')
                
                return redirect(next_page)
            else:
                app.logger.warning(f"Failed login attempt for username: {username}")
                flash('Invalid username or password', 'danger')
        except Exception as e:
            app.logger.error(f"Error during login: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
    
    return render_template('login.html', form=form)
"""
            # Find a good place to add the login route
            admin_route_start = content.find("@app.route('/admin')")
            if admin_route_start > 0:
                # Find the end of the admin_index function
                admin_function_end = content.find("@app.route", admin_route_start + 10)
                if admin_function_end > 0:
                    updated_content = content[:admin_function_end] + login_route + content[admin_function_end:]
                    
                    with open(app_py_path, 'w') as f:
                        f.write(updated_content)
                    
                    logger.info("Added robust login route")
                    return True
                else:
                    logger.error("Could not find end of admin_index function")
                    return False
            else:
                logger.error("Could not find admin route")
                return False
        else:
            # Check if the login route has proper error handling
            login_function_start = login_route_match.end()
            next_route_start = content.find("@app.route", login_function_start)
            login_function = content[login_function_start:next_route_start]
            
            if "try:" not in login_function or "except Exception as e:" not in login_function:
                logger.warning("Login route might not have proper error handling")
            else:
                logger.info("Login route has proper error handling")
            
            return True
    
    except Exception as e:
        logger.error(f"Error fixing admin login route: {str(e)}")
        return False

def add_error_template():
    """Add error template if it doesn't exist"""
    logger.info("Checking for error templates...")
    
    error_templates = [
        'templates/errors/404.html',
        'templates/errors/500.html'
    ]
    
    for template_path in error_templates:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        if not os.path.exists(template_path):
            logger.warning(f"Error template {template_path} not found, creating...")
            
            if '404' in template_path:
                template_content = """{% extends "base.html" %}

{% block title %}404 - Sayfa Bulunamadı{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row">
        <div class="col-md-8 offset-md-2 text-center">
            <div class="card">
                <div class="card-header bg-danger text-white">
                    <h4 class="mb-0">Sayfa Bulunamadı</h4>
                </div>
                <div class="card-body">
                    <div class="mb-4">
                        <i class="fas fa-exclamation-triangle text-danger fa-5x mb-3"></i>
                        <h2>404 Hata</h2>
                        <p class="lead">Aradığınız sayfa bulunamadı.</p>
                    </div>
                    
                    <p>Sayfanın taşınmış veya silinmiş olabilir.</p>
                    
                    <div class="mt-4">
                        <a href="{{ url_for('index') }}" class="btn btn-primary">
                            <i class="fas fa-home me-2"></i> Ana Sayfaya Dön
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""
            else:
                template_content = """{% extends "base.html" %}

{% block title %}500 - Sunucu Hatası{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row">
        <div class="col-md-8 offset-md-2 text-center">
            <div class="card">
                <div class="card-header bg-danger text-white">
                    <h4 class="mb-0">Sunucu Hatası</h4>
                </div>
                <div class="card-body">
                    <div class="mb-4">
                        <i class="fas fa-exclamation-circle text-danger fa-5x mb-3"></i>
                        <h2>Üzgünüz, bir sorun oluştu</h2>
                        <p class="lead">Sunucu beklenmedik bir hata ile karşılaştı ve isteğinizi şu anda işleyemiyor.</p>
                    </div>
                    
                    <p>Lütfen daha sonra tekrar deneyiniz. Sorun devam ederse site yöneticisiyle iletişime geçin.</p>
                    
                    <div class="mt-4">
                        <a href="{{ url_for('index') }}" class="btn btn-primary">
                            <i class="fas fa-home me-2"></i> Ana Sayfaya Dön
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""
            
            with open(template_path, 'w') as f:
                f.write(template_content)
            
            logger.info(f"Created error template: {template_path}")
    
    logger.info("Error templates check completed")
    return True

def fix_admin_redirect():
    """Check for proper redirects in admin routes"""
    logger.info("Checking admin redirects...")
    
    app_py_path = 'app.py'
    
    try:
        with open(app_py_path, 'r') as f:
            content = f.read()
        
        # Check for url_for calls to non-existent functions
        admin_redirects = re.findall(r'redirect\(url_for\([\'\"](admin_\w+)[\'\"]\)\)', content)
        function_defs = re.findall(r'def\s+(admin_\w+)\(', content)
        
        function_defs_set = set(function_defs)
        
        missing_redirects = [redirect for redirect in admin_redirects if redirect not in function_defs_set]
        
        if missing_redirects:
            logger.warning(f"Found redirects to non-existent functions: {missing_redirects}")
            
            # Fix each broken redirect
            fixed_content = content
            for missing in missing_redirects:
                # Map to a valid route
                if 'admin_index' in function_defs_set:
                    fixed_content = fixed_content.replace(
                        f"redirect(url_for('{missing}'))",
                        f"redirect(url_for('admin_index'))"
                    )
                    logger.info(f"Fixed redirect from '{missing}' to 'admin_index'")
            
            if fixed_content != content:
                with open(app_py_path, 'w') as f:
                    f.write(fixed_content)
                
                logger.info("Fixed admin redirects")
                return True
        else:
            logger.info("All admin redirects are valid")
            return True
    
    except Exception as e:
        logger.error(f"Error fixing admin redirects: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting admin login fix process...")
    
    # Add error templates if needed
    add_error_template()
    
    # Fix login_required decorator if needed
    fix_login_required_decorator()
    
    # Fix admin login route if needed
    fix_admin_login_route()
    
    # Fix admin redirects if needed
    fix_admin_redirect()
    
    logger.info("Admin login fixes completed")
    
    print("\nTo apply these fixes, restart the Flask application.")
    print("If the issue persists, check the error logs and ensure all templates are available.") 