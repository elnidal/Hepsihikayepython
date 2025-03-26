from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm, CSRFProtect
from flask_ckeditor import CKEditor, CKEditorField
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(level=logging.INFO)
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# App configuration
app.secret_key = os.environ.get('SECRET_KEY', 'hepsihikaye-dev-key')
app.config['UPLOADS_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['DEBUG'] = True
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_HEIGHT'] = 400
app.config['CKEDITOR_PKG_TYPE'] = 'standard'

# Configure logger
if not app.logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('Application startup')

# Initialize extensions
csrf = CSRFProtect(app)
ckeditor = CKEditor(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Lütfen giriş yapın!'
login_manager.login_message_category = 'warning'

# Data storage configuration
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

POSTS_FILE = os.path.join(DATA_DIR, 'posts.json')
VIDEOS_FILE = os.path.join(DATA_DIR, 'videos.json')
CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')
COMMENTS_FILE = os.path.join(DATA_DIR, 'comments.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# File-based data helpers
def load_data(file_path, default=None):
    """Load data from a JSON file or return default if file doesn't exist"""
    if default is None:
        default = []
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default
    except Exception as e:
        app.logger.error(f"Error loading data from {file_path}: {str(e)}")
        return default

def save_data(file_path, data):
    """Save data to a JSON file"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        app.logger.error(f"Error saving data to {file_path}: {str(e)}")
        return False

def format_datetime(dt_str):
    """Format a datetime string for display"""
    if isinstance(dt_str, str):
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime('%d.%m.%Y %H:%M')
        except:
            return dt_str
    return dt_str

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.password = user_data['password']

    @staticmethod
    def get(user_id):
        users = load_data(USERS_FILE, [])
        for user_data in users:
            if user_data['id'] == user_id:
                return User(user_data)
        return None

    def check_password(self, password):
        return check_password_hash(self.password, password)

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

def init_file_data():
    """Initialize the file-based data storage with default values"""
    # Default categories
    default_categories = [
        {'id': 1, 'name': 'Öykü', 'slug': 'oyku'},
        {'id': 2, 'name': 'Roman', 'slug': 'roman'},
        {'id': 3, 'name': 'Şiir', 'slug': 'siir'},
        {'id': 4, 'name': 'Deneme', 'slug': 'deneme'},
        {'id': 5, 'name': 'İnceleme', 'slug': 'inceleme'},
        {'id': 6, 'name': 'Haber', 'slug': 'haber'},
        {'id': 7, 'name': 'Video', 'slug': 'video'}
    ]
    
    # Default admin user
    default_users = [
        {'id': 1, 'username': 'admin', 'password': generate_password_hash('admin')}
    ]
    
    # Default welcome post
    default_posts = [
        {
            'id': 1,
            'title': 'Hoş Geldiniz',
            'content': 'Hepsi Hikaye web sitesine hoş geldiniz. Bu bir örnek içeriktir.',
            'created_at': datetime.now().isoformat(),
            'category_id': 1,
            'views': 0,
            'likes': 0,
            'dislikes': 0,
            'published': True,
            'featured': True
        }
    ]
    
    # Load or create default data files
    load_data(CATEGORIES_FILE, default_categories)
    load_data(POSTS_FILE, default_posts)
    load_data(VIDEOS_FILE, [])
    load_data(COMMENTS_FILE, [])
    load_data(USERS_FILE, default_users)
    
    app.logger.info("File-based data initialization complete")

# Routes
@app.route('/')
def index():
    try:
        posts = load_data(POSTS_FILE, [])
        videos = load_data(VIDEOS_FILE, [])
        
        # Sort by created_at
        posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        videos.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Format dates and add image URLs
        for post in posts:
            if isinstance(post.get('created_at'), str):
                post['formatted_date'] = format_datetime(post['created_at'])
            post['image_url'] = url_for('static', filename=f'uploads/{post.get("image", "default-post.jpg")}')
        
        # Format dates for videos
        for video in videos:
            if isinstance(video.get('created_at'), str):
                video['formatted_date'] = format_datetime(video['created_at'])
        
        # Limit to recent items
        recent_posts = posts[:6]
        recent_videos = videos[:3]
        
        return render_template('index.html', posts=recent_posts, videos=recent_videos)
    except Exception as e:
        app.logger.error(f"Index error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        users = load_data(USERS_FILE, [])
        user_data = next((u for u in users if u['username'] == username), None)
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user, remember=remember)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre.', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    try:
        posts = load_data(POSTS_FILE, [])
        videos = load_data(VIDEOS_FILE, [])
        comments = load_data(COMMENTS_FILE, [])
        
        total_posts = len(posts)
        total_videos = len(videos)
        total_comments = len(comments)
        total_views = sum(post.get('views', 0) for post in posts)
        
        recent_posts = sorted(posts, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        recent_videos = sorted(videos, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
        
        return render_template(
            'admin/dashboard.html',
            total_posts=total_posts,
            total_videos=total_videos,
            total_comments=total_comments,
            total_views=total_views,
            recent_posts=recent_posts,
            recent_videos=recent_videos
        )
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {str(e)}")
        return redirect(url_for('admin_login'))

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    try:
        posts = load_data(POSTS_FILE, [])
        post = next((p for p in posts if p['id'] == post_id), None)
        
        if not post:
            return render_template('errors/404.html'), 404
        
        # Increment views
        post['views'] = post.get('views', 0) + 1
        save_data(POSTS_FILE, posts)
        
        # Get comments
        comments = load_data(COMMENTS_FILE, [])
        post_comments = [c for c in comments if c.get('post_id') == post_id]
        
        # Format dates
        for comment in post_comments:
            comment['formatted_date'] = format_datetime(comment.get('created_at', ''))
        
        return render_template('post.html', post=post, comments=post_comments)
    except Exception as e:
        app.logger.error(f"Post detail error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    try:
        name = request.form.get('name')
        content = request.form.get('content')
        
        if not name or not content:
            flash('İsim ve yorum alanları zorunludur.', 'danger')
            return redirect(url_for('post_detail', post_id=post_id))
        
        comments = load_data(COMMENTS_FILE, [])
        new_comment = {
            'id': len(comments) + 1,
            'author_name': name,
            'content': content,
            'post_id': post_id,
            'created_at': datetime.now().isoformat()
        }
        
        comments.append(new_comment)
        save_data(COMMENTS_FILE, comments)
        
        flash('Yorumunuz başarıyla eklendi.', 'success')
        return redirect(url_for('post_detail', post_id=post_id))
    except Exception as e:
        app.logger.error(f"Add comment error: {str(e)}")
        flash('Yorumunuz eklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))

@app.route('/post/<int:post_id>/rate/<action>', methods=['POST'])
def rate_post(post_id, action):
    try:
        if action not in ['like', 'dislike']:
            return jsonify({'success': False, 'message': 'Geçersiz işlem.'})
        
        posts = load_data(POSTS_FILE, [])
        post = next((p for p in posts if p['id'] == post_id), None)
        
        if not post:
            return jsonify({'success': False, 'message': 'Gönderi bulunamadı.'})
        
        if action == 'like':
            post['likes'] = post.get('likes', 0) + 1
        else:
            post['dislikes'] = post.get('dislikes', 0) + 1
        
        save_data(POSTS_FILE, posts)
        
        return jsonify({
            'success': True,
            'likes': post.get('likes', 0),
            'dislikes': post.get('dislikes', 0),
            'message': 'Oyunuz kaydedildi!'
        })
    except Exception as e:
        app.logger.error(f"Rate post error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
        })

@app.route('/admin/posts')
@login_required
def admin_posts():
    try:
        posts = load_data(POSTS_FILE, [])
        search_query = request.args.get('search', '')
        
        if search_query:
            posts = [p for p in posts if 
                    search_query.lower() in p.get('title', '').lower() or 
                    search_query.lower() in p.get('content', '').lower()]
        
        return render_template('admin/posts.html', posts=posts, search_query=search_query)
    except Exception as e:
        app.logger.error(f"Admin posts error: {str(e)}")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    try:
        categories = load_data(CATEGORIES_FILE, [])
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            category_id = request.form.get('category_id')
            excerpt = request.form.get('excerpt')
            published = request.form.get('published') == 'on'
            featured = request.form.get('featured') == 'on'
            image = request.files.get('image')
            
            if not title or not content:
                flash('Başlık ve içerik alanları zorunludur.', 'error')
                return render_template('admin/post_form.html', categories=categories)
            
            posts = load_data(POSTS_FILE, [])
            new_post = {
                'id': len(posts) + 1,
                'title': title,
                'content': content,
                'category_id': int(category_id) if category_id else None,
                'excerpt': excerpt,
                'published': published,
                'featured': featured,
                'views': 0,
                'likes': 0,
                'dislikes': 0,
                'created_at': datetime.now().isoformat()
            }
            
            if image and image.filename:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.static_folder, 'uploads', filename)
                image.save(image_path)
                new_post['image'] = filename
            
            posts.append(new_post)
            save_data(POSTS_FILE, posts)
            
            flash('Gönderi başarıyla oluşturuldu.', 'success')
            return redirect(url_for('admin_posts'))
        
        return render_template('admin/post_form.html', categories=categories)
    except Exception as e:
        app.logger.error(f"New post error: {str(e)}")
        flash('Gönderi oluşturulurken bir hata oluştu.', 'error')
        return redirect(url_for('admin_posts'))

@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    try:
        posts = load_data(POSTS_FILE, [])
        categories = load_data(CATEGORIES_FILE, [])
        post = next((p for p in posts if p['id'] == post_id), None)
        
        if not post:
            flash('Gönderi bulunamadı.', 'error')
            return redirect(url_for('admin_posts'))
        
        if request.method == 'POST':
            post['title'] = request.form.get('title')
            post['content'] = request.form.get('content')
            post['category_id'] = int(request.form.get('category_id')) if request.form.get('category_id') else None
            post['excerpt'] = request.form.get('excerpt')
            post['published'] = request.form.get('published') == 'on'
            post['featured'] = request.form.get('featured') == 'on'
            
            image = request.files.get('image')
            remove_image = request.form.get('remove_image') == 'on'
            
            if remove_image and post.get('image'):
                old_image_path = os.path.join(app.static_folder, 'uploads', post['image'])
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
                post['image'] = None
            
            if image and image.filename:
                if post.get('image'):
                    old_image_path = os.path.join(app.static_folder, 'uploads', post['image'])
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.static_folder, 'uploads', filename)
                image.save(image_path)
                post['image'] = filename
            
            save_data(POSTS_FILE, posts)
            flash('Gönderi başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_posts'))
        
        return render_template('admin/post_form.html', post=post, categories=categories)
    except Exception as e:
        app.logger.error(f"Edit post error: {str(e)}")
        flash('Gönderi güncellenirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_posts'))

@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    try:
        posts = load_data(POSTS_FILE, [])
        post = next((p for p in posts if p['id'] == post_id), None)
        
        if post:
            if post.get('image'):
                image_path = os.path.join(app.static_folder, 'uploads', post['image'])
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            posts = [p for p in posts if p['id'] != post_id]
            save_data(POSTS_FILE, posts)
            flash('Gönderi başarıyla silindi.', 'success')
    except Exception as e:
        app.logger.error(f"Delete post error: {str(e)}")
        flash('Gönderi silinirken bir hata oluştu.', 'error')
    
    return redirect(url_for('admin_posts'))

@app.route('/admin/categories')
@login_required
def admin_categories():
    try:
        categories = load_data(CATEGORIES_FILE, [])
        return render_template('admin/categories.html', categories=categories)
    except Exception as e:
        app.logger.error(f"Admin categories error: {str(e)}")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/categories/new', methods=['POST'])
@login_required
def admin_new_category():
    try:
        name = request.form.get('name')
        slug = request.form.get('slug')
        
        if not name or not slug:
            flash('Kategori adı ve slug gereklidir.', 'danger')
            return redirect(url_for('admin_categories'))
        
        categories = load_data(CATEGORIES_FILE, [])
        
        # Check if category with same name or slug exists
        if any(c['name'] == name or c['slug'] == slug for c in categories):
            flash('Bu isim veya slug ile bir kategori zaten mevcut.', 'danger')
            return redirect(url_for('admin_categories'))
        
        new_category = {
            'id': len(categories) + 1,
            'name': name,
            'slug': slug
        }
        
        categories.append(new_category)
        save_data(CATEGORIES_FILE, categories)
        flash('Kategori başarıyla oluşturuldu.', 'success')
    except Exception as e:
        app.logger.error(f"New category error: {str(e)}")
        flash('Kategori oluşturulurken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def admin_delete_category(category_id):
    try:
        categories = load_data(CATEGORIES_FILE, [])
        posts = load_data(POSTS_FILE, [])
        
        # Update posts with this category to have no category
        for post in posts:
            if post.get('category_id') == category_id:
                post['category_id'] = None
        
        # Remove the category
        categories = [c for c in categories if c['id'] != category_id]
        
        save_data(CATEGORIES_FILE, categories)
        save_data(POSTS_FILE, posts)
        flash('Kategori başarıyla silindi.', 'success')
    except Exception as e:
        app.logger.error(f"Delete category error: {str(e)}")
        flash('Kategori silinirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/comments')
@login_required
def admin_comments():
    try:
        comments = load_data(COMMENTS_FILE, [])
        return render_template('admin/comments.html', comments=comments)
    except Exception as e:
        app.logger.error(f"Admin comments error: {str(e)}")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    try:
        comments = load_data(COMMENTS_FILE, [])
        comments = [c for c in comments if c['id'] != comment_id]
        save_data(COMMENTS_FILE, comments)
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Delete comment error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/change-password', methods=['POST'])
@login_required
def admin_change_password():
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Tüm alanları doldurun.', 'error')
            return redirect(url_for('admin_settings'))
        
        if new_password != confirm_password:
            flash('Yeni şifreler eşleşmiyor.', 'error')
            return redirect(url_for('admin_settings'))
        
        users = load_data(USERS_FILE, [])
        user = next((u for u in users if u['id'] == current_user.id), None)
        
        if not user or not check_password_hash(user['password'], current_password):
            flash('Mevcut şifre yanlış.', 'error')
            return redirect(url_for('admin_settings'))
        
        user['password'] = generate_password_hash(new_password)
        save_data(USERS_FILE, users)
        
        flash('Şifreniz başarıyla güncellendi.', 'success')
        return redirect(url_for('admin_settings'))
    except Exception as e:
        app.logger.error(f"Change password error: {str(e)}")
        flash('Şifre değiştirilirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_settings'))

@app.route('/admin/settings')
@login_required
def admin_settings():
    try:
        return render_template('admin/settings.html')
    except Exception as e:
        app.logger.error(f"Admin settings error: {str(e)}")
        flash('Ayarlar yüklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.context_processor
def inject_categories():
    try:
        categories = load_data(CATEGORIES_FILE, [])
        return dict(categories=categories)
    except Exception as e:
        app.logger.error(f"Category injection error: {str(e)}")
        return dict(categories=[])

if __name__ == '__main__':
    # Ensure required directories exist
    for directory in ['uploads', 'images', 'data', 'logs']:
        path = os.path.join(app.static_folder, directory)
        if not os.path.exists(path):
            os.makedirs(path)
            app.logger.info(f"Created directory: {path}")
    
    # Initialize data
    init_file_data()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
else:
    # This code runs when imported (e.g., by Gunicorn in production)
    # Ensure required directories exist
    for directory in ['uploads', 'images', 'data', 'logs']:
        path = os.path.join(app.static_folder, directory)
        if not os.path.exists(path):
            os.makedirs(path)
            app.logger.info(f"Created directory: {path}")
    
    # Initialize data
    init_file_data() 