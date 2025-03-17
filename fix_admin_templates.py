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

def check_template_paths():
    """Check if template paths in app.py match the actual file structure"""
    logger.info("Checking template paths in app.py...")
    
    app_py_path = 'app.py'
    
    try:
        with open(app_py_path, 'r') as f:
            content = f.read()
        
        # Find all render_template calls
        template_pattern = r'render_template\([\'\"]([\w\/\.]+)[\'\"]'
        template_matches = re.findall(template_pattern, content)
        
        logger.info(f"Found {len(template_matches)} template references")
        
        # Check if templates exist
        missing_templates = []
        for template in template_matches:
            template_path = os.path.join('templates', template)
            if not os.path.exists(template_path):
                missing_templates.append(template)
                logger.warning(f"Template not found: {template_path}")
        
        if missing_templates:
            logger.error(f"Found {len(missing_templates)} missing templates")
        else:
            logger.info("All template references are valid")
        
        return missing_templates
    
    except Exception as e:
        logger.error(f"Error checking template paths: {str(e)}")
        return []

def fix_admin_template_references():
    """Fix references to admin templates in app.py"""
    logger.info("Fixing admin template references...")
    
    app_py_path = 'app.py'
    
    try:
        with open(app_py_path, 'r') as f:
            content = f.read()
            
        # Check for common admin template path issues and fix them
        fixes = {
            # Old format to new format
            'render_template(\'admin/index.html\'': 'render_template(\'admin/dashboard.html\'',
            'render_template("admin/index.html"': 'render_template("admin/dashboard.html"',
            'render_template(\'admin/create_post.html\'': 'render_template(\'admin/new_post.html\'',
            'render_template("admin/create_post.html"': 'render_template("admin/new_post.html"',
            'render_template(\'admin/add_video.html\'': 'render_template(\'admin/new_video.html\'',
            'render_template("admin/add_video.html"': 'render_template("admin/new_video.html"',
            'render_template(\'admin/sync_youtube.html\'': 'render_template(\'admin/youtube_sync.html\'',
            'render_template("admin/sync_youtube.html"': 'render_template("admin/youtube_sync.html"',
        }
        
        updated_content = content
        for old, new in fixes.items():
            if old in updated_content:
                updated_content = updated_content.replace(old, new)
                logger.info(f"Fixed template reference: {old} -> {new}")
        
        # Make sure dashboard template includes active_page parameter
        dashboard_pattern = r'(render_template\([\'\"](admin\/dashboard\.html)[\'\"],\s*posts=posts,\s*videos=videos)(\))'
        if re.search(dashboard_pattern, updated_content):
            updated_content = re.sub(dashboard_pattern, r'\1, active_page="dashboard"\3', updated_content)
            logger.info("Added active_page parameter to dashboard template reference")
        
        # Ensure new_post template includes active_page parameter
        new_post_pattern = r'(render_template\([\'\"](admin\/new_post\.html)[\'\"],\s*form=form,\s*categories=categories)(\))'
        if re.search(new_post_pattern, updated_content):
            updated_content = re.sub(new_post_pattern, r'\1, active_page="new_post"\3', updated_content)
            logger.info("Added active_page parameter to new_post template reference")
        
        # Ensure new_video template includes active_page parameter
        new_video_pattern = r'(render_template\([\'\"](admin\/new_video\.html)[\'\"],\s*form=form)(\))'
        if re.search(new_video_pattern, updated_content):
            updated_content = re.sub(new_video_pattern, r'\1, active_page="new_video"\3', updated_content)
            logger.info("Added active_page parameter to new_video template reference")
        
        # Save changes if any were made
        if updated_content != content:
            with open(app_py_path, 'w') as f:
                f.write(updated_content)
            logger.info("Successfully updated template references")
            return True
        else:
            logger.info("No template reference changes needed")
            return False
    
    except Exception as e:
        logger.error(f"Error fixing template references: {str(e)}")
        return False

def create_missing_admin_templates():
    """Create any missing admin templates based on renamed files"""
    logger.info("Checking for potential renamed admin templates...")
    
    templates_dir = 'templates/admin'
    os.makedirs(templates_dir, exist_ok=True)
    
    # Map potential renamed templates
    template_mapping = {
        'index.html': 'dashboard.html',
        'create_post.html': 'new_post.html',
        'add_video.html': 'new_video.html',
        'sync_youtube.html': 'youtube_sync.html'
    }
    
    for old_name, new_name in template_mapping.items():
        old_path = os.path.join(templates_dir, old_name)
        new_path = os.path.join(templates_dir, new_name)
        
        # If the old template exists but the new one doesn't
        if os.path.exists(old_path) and not os.path.exists(new_path):
            logger.info(f"Creating {new_path} based on {old_path}")
            
            # Read the old template
            with open(old_path, 'r') as f:
                content = f.read()
            
            # Write to the new template
            with open(new_path, 'w') as f:
                f.write(content)
            
            logger.info(f"Created {new_name} from {old_name}")
        
        # If neither exists, create a minimal version of the new template
        elif not os.path.exists(new_path):
            logger.warning(f"Neither {old_name} nor {new_name} exists. Creating minimal {new_name}")
            
            # Create minimal template based on the type
            if new_name == 'dashboard.html':
                template_content = """{% extends "admin/base.html" %}

{% block admin_content %}
<h1>Dashboard</h1>

<div class="row">
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header">
                <h5>Hikayeler</h5>
            </div>
            <div class="card-body">
                {% if posts %}
                <table class="table">
                    <thead>
                        <tr>
                            <th>Başlık</th>
                            <th>Kategori</th>
                            <th>İşlemler</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for post in posts %}
                        <tr>
                            <td>{{ post.title }}</td>
                            <td>{{ post.category }}</td>
                            <td>
                                <a href="{{ url_for('admin_edit_post', post_id=post.id) }}" class="btn btn-sm btn-primary">
                                    <i class="fas fa-edit"></i>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>Henüz hikaye eklenmemiş.</p>
                {% endif %}
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header">
                <h5>Videolar</h5>
            </div>
            <div class="card-body">
                {% if videos %}
                <table class="table">
                    <thead>
                        <tr>
                            <th>Başlık</th>
                            <th>İşlemler</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for video in videos %}
                        <tr>
                            <td>{{ video.title }}</td>
                            <td>
                                <a href="{{ url_for('admin_edit_video', video_id=video.id) }}" class="btn btn-sm btn-primary">
                                    <i class="fas fa-edit"></i>
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>Henüz video eklenmemiş.</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}"""
            elif new_name == 'new_post.html':
                template_content = """{% extends "admin/base.html" %}

{% block admin_content %}
<h1>Yeni Hikaye Ekle</h1>

<div class="card">
    <div class="card-body">
        <form method="POST" enctype="multipart/form-data">
            {{ form.hidden_tag() }}
            
            <div class="mb-3">
                <label for="title" class="form-label">Başlık</label>
                {{ form.title(class="form-control") }}
                {% if form.title.errors %}
                <div class="text-danger">
                    {% for error in form.title.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <div class="mb-3">
                <label for="category" class="form-label">Kategori</label>
                {{ form.category(class="form-control") }}
                {% if form.category.errors %}
                <div class="text-danger">
                    {% for error in form.category.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <div class="mb-3">
                <label for="content" class="form-label">İçerik</label>
                {{ form.content(class="form-control", rows=10) }}
                {% if form.content.errors %}
                <div class="text-danger">
                    {% for error in form.content.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <div class="mb-3">
                <label for="image" class="form-label">Görsel</label>
                {{ form.image(class="form-control") }}
                {% if form.image.errors %}
                <div class="text-danger">
                    {% for error in form.image.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <button type="submit" class="btn btn-primary">Kaydet</button>
        </form>
    </div>
</div>
{% endblock %}"""
            elif new_name == 'new_video.html':
                template_content = """{% extends "admin/base.html" %}

{% block admin_content %}
<h1>Yeni Video Ekle</h1>

<div class="card">
    <div class="card-body">
        <form method="POST">
            {{ form.hidden_tag() }}
            
            <div class="mb-3">
                <label for="title" class="form-label">Başlık</label>
                {{ form.title(class="form-control") }}
                {% if form.title.errors %}
                <div class="text-danger">
                    {% for error in form.title.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <div class="mb-3">
                <label for="youtube_id" class="form-label">YouTube ID</label>
                {{ form.youtube_id(class="form-control") }}
                {% if form.youtube_id.errors %}
                <div class="text-danger">
                    {% for error in form.youtube_id.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <div class="mb-3">
                <label for="description" class="form-label">Açıklama</label>
                {{ form.description(class="form-control", rows=5) }}
                {% if form.description.errors %}
                <div class="text-danger">
                    {% for error in form.description.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <button type="submit" class="btn btn-primary">Kaydet</button>
        </form>
    </div>
</div>
{% endblock %}"""
            elif new_name == 'youtube_sync.html':
                template_content = """{% extends "admin/base.html" %}

{% block admin_content %}
<h1>YouTube Videolarını Senkronize Et</h1>

<div class="card">
    <div class="card-body">
        <form method="POST">
            {{ form.hidden_tag() }}
            
            <div class="mb-3">
                <label for="channel_id" class="form-label">YouTube Kanal ID</label>
                {{ form.channel_id(class="form-control") }}
                {% if form.channel_id.errors %}
                <div class="text-danger">
                    {% for error in form.channel_id.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <div class="mb-3">
                <label for="max_results" class="form-label">Maksimum Video Sayısı</label>
                {{ form.max_results(class="form-control") }}
                {% if form.max_results.errors %}
                <div class="text-danger">
                    {% for error in form.max_results.errors %}
                    {{ error }}
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            
            <button type="submit" class="btn btn-primary">Senkronize Et</button>
        </form>
    </div>
</div>

{% if sync_results %}
<div class="card mt-4">
    <div class="card-header">
        <h5>Senkronizasyon Sonuçları</h5>
    </div>
    <div class="card-body">
        <p>{{ sync_results }}</p>
    </div>
</div>
{% endif %}
{% endblock %}"""
            else:
                template_content = """{% extends "admin/base.html" %}

{% block admin_content %}
<h1>Admin Paneli</h1>
<p>Bu şablon geçici olarak oluşturuldu.</p>
{% endblock %}"""
            
            with open(new_path, 'w') as f:
                f.write(template_content)
            
            logger.info(f"Created minimal template for {new_name}")
    
    logger.info("Missing admin template check completed")
    return True

def create_admin_base_template():
    """Create admin base template if it doesn't exist"""
    logger.info("Checking for admin base template...")
    
    templates_dir = 'templates/admin'
    os.makedirs(templates_dir, exist_ok=True)
    
    base_path = os.path.join(templates_dir, 'base.html')
    
    if not os.path.exists(base_path):
        logger.warning("Admin base template not found, creating...")
        
        template_content = """{% extends "base.html" %}

{% block title %}Admin Panel - HepsiHikaye{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <!-- Sidebar -->
        <div class="col-md-3 col-lg-2 d-md-block bg-dark sidebar">
            <div class="position-sticky pt-3">
                <h5 class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-white">
                    Admin Panel
                </h5>
                <ul class="nav flex-column">
                    <li class="nav-item">
                        <a class="nav-link {{ 'active' if active_page == 'dashboard' }}" href="{{ url_for('admin_index') }}">
                            <i class="fas fa-tachometer-alt"></i> Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {{ 'active' if active_page == 'new_post' }}" href="{{ url_for('admin_new_post') }}">
                            <i class="fas fa-pen"></i> Yeni Hikaye
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {{ 'active' if active_page == 'new_video' }}" href="{{ url_for('admin_new_video') }}">
                            <i class="fas fa-video"></i> Video Ekle
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {{ 'active' if active_page == 'youtube_sync' }}" href="{{ url_for('admin_youtube_sync') }}">
                            <i class="fab fa-youtube"></i> YouTube Senkronizasyon
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {{ 'active' if active_page == 'comments' }}" href="{{ url_for('admin_comments') }}">
                            <i class="fas fa-comments"></i> Yorumlar
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {{ 'active' if active_page == 'settings' }}" href="{{ url_for('admin_settings') }}">
                            <i class="fas fa-cog"></i> Ayarlar
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">
                            <i class="fas fa-arrow-left"></i> Siteye Dön
                        </a>
                    </li>
                </ul>
            </div>
        </div>
        
        <!-- Main content -->
        <div class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
            <div class="mt-4">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">
                                {{ message }}
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                {% block admin_content %}{% endblock %}
            </div>
        </div>
    </div>
</div>

<style>
    .sidebar {
        min-height: calc(100vh - 60px);
    }
    
    .sidebar .nav-link {
        color: rgba(255, 255, 255, 0.6);
        padding: 0.75rem 1rem;
    }
    
    .sidebar .nav-link.active {
        color: #fff;
        background-color: rgba(255, 255, 255, 0.1);
    }
    
    .sidebar .nav-link:hover {
        color: #fff;
    }
    
    .sidebar .nav-link i {
        margin-right: 0.5rem;
    }
</style>
{% endblock %}"""
        
        with open(base_path, 'w') as f:
            f.write(template_content)
        
        logger.info("Created admin base template")
    else:
        logger.info("Admin base template exists")
    
    return True

if __name__ == "__main__":
    logger.info("Starting admin template fix process...")
    
    # Create admin/base.html if missing
    create_admin_base_template()
    
    # Create missing templates based on renamed files
    create_missing_admin_templates()
    
    # Check template paths in app.py
    missing_templates = check_template_paths()
    
    # Fix template references in app.py
    fix_admin_template_references()
    
    logger.info("Admin template fixes completed")
    
    # Print a summary
    print("\nAdmin Template Fix Summary:")
    print("1. Created or verified admin/base.html template")
    print("2. Created missing admin templates or checked for renamed ones")
    print(f"3. Found {len(missing_templates)} missing template references in app.py")
    print("4. Fixed template references in app.py\n")
    
    print("To apply these fixes, restart the Flask application.") 