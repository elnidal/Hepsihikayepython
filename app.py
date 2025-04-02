from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm, CSRFProtect
from flask_ckeditor import CKEditor, CKEditorField
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired, ValidationError
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_wtf.csrf import validate_csrf
from supabase import create_client, Client

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
app.config['CKEDITOR_ENABLE_CSRF'] = True
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'  # Set the upload route for CKEditor

# Supabase Configuration
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

if not supabase_url or not supabase_key:
    app.logger.warning("Supabase URL or Key not found in environment variables. Storage uploads will fail.")
    supabase = None
else:
    try:
        supabase = create_client(supabase_url, supabase_key)
        app.logger.info("Supabase client initialized successfully.")
    except Exception as e:
        app.logger.error(f"Failed to initialize Supabase client: {e}")
        supabase = None

# Function to upload files to Supabase
def upload_to_supabase(file, folder="posts"):
    """
    Upload a file to Supabase Storage and return its public URL
    
    Parameters:
    - file: The file object from Flask request
    - folder: The folder within the bucket to store the file (default: "posts")
    
    Returns:
    - The public URL of the uploaded file, or None if upload failed
    """
    if not supabase or not file:
        return None
        
    try:
        # Generate a unique filename
        original_filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().timestamp()}_{original_filename}"
        supabase_path = f"{folder}/{unique_filename}"
        
        app.logger.info(f"Uploading to Supabase bucket 'uploads' at path: {supabase_path}")
        
        # Reset file pointer and read data
        file.seek(0)
        file_data = file.read()
        
        # Get content type
        content_type = file.content_type or 'application/octet-stream'
        
        # Upload to Supabase Storage
        supabase.storage.from_("uploads").upload(
            path=supabase_path,
            file=file_data,
            file_options={"content-type": content_type}
        )
        
        # Get the public URL
        public_url = supabase.storage.from_("uploads").get_public_url(supabase_path)
        app.logger.info(f"Successfully uploaded to Supabase. Public URL: {public_url}")
        
        return public_url
        
    except Exception as e:
        app.logger.error(f"Supabase upload failed: {e}")
        return None

# Database configuration
database_url = os.environ.get('DATABASE_URL')
# Fix URI format for SQLAlchemy if needed
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if not database_url and not app.config['DEBUG']:
    raise ValueError("DATABASE_URL environment variable is not set")
elif not database_url and app.config['DEBUG']:
    # Use SQLite for local development if no DATABASE_URL is provided
    database_url = 'sqlite:///hepsihikaye.db'
    app.logger.warning("Using SQLite for local development. Set DATABASE_URL for PostgreSQL.")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    posts = db.relationship('Post', backref='category', lazy=True)
    videos = db.relationship('Video', backref='category', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    image = db.Column(db.String(200))
    author = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    published = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    published = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    comments = db.relationship('Comment', backref='video', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class EmailSettings(db.Model):
    __tablename__ = 'email_settings'
    id = db.Column(db.Integer, primary_key=True)
    smtp_server = db.Column(db.String(255), nullable=False)
    smtp_port = db.Column(db.Integer, nullable=False)
    smtp_username = db.Column(db.String(255), nullable=False)
    smtp_password = db.Column(db.String(255), nullable=False)
    default_from_email = db.Column(db.String(255), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RegistrationSettings(db.Model):
    __tablename__ = 'registration_settings'
    id = db.Column(db.Integer, primary_key=True)
    enable_registration = db.Column(db.Boolean, default=True)
    require_email_verification = db.Column(db.Boolean, default=True)
    allow_guest_posts = db.Column(db.Boolean, default=False)
    default_user_role = db.Column(db.String(50), default='user')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

# Custom Jinja Filters
@app.template_filter('format_datetime_filter')
def format_datetime_filter(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%d.%m.%Y %H:%M')
    elif isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
            return dt.strftime('%d.%m.%Y %H:%M')
        except:
            return dt # Return original string if parsing fails
    return dt

@app.template_filter('post_image_url')
def post_image_url_filter(post):
    if hasattr(post, 'image') and post.image:
        # If the image is already a full URL (from Supabase), return it directly
        if post.image.startswith('http'):
            return post.image
        # Otherwise, treat it as a local file
        return url_for('static', filename=f'uploads/{post.image}')
    return url_for('static', filename='uploads/default_post_image.png')

@app.template_filter('video_thumbnail_url')
def video_thumbnail_url_filter(video):
    """Generate URL for video thumbnail or default image."""
    if hasattr(video, 'thumbnail_url') and video.thumbnail_url:
        # If the thumbnail is already a full URL (from Supabase), return it directly
        if video.thumbnail_url.startswith('http'):
            return video.thumbnail_url
        # Otherwise, treat thumbnail_url as a filename
        return url_for('static', filename=f'uploads/{video.thumbnail_url}')
    # Provide a default video thumbnail
    return url_for('static', filename='uploads/default_video_thumb.png')

# Routes
@app.route('/')
def index():
    try:
        # Get trending posts (most liked and most viewed posts)
        trending_posts = Post.query.filter_by(published=True) \
            .order_by((Post.likes * 2 + Post.views).desc()) \
            .limit(3).all()
        
        # Get recent posts (exclude trending ones to avoid duplication)
        trending_ids = [post.id for post in trending_posts]
        recent_posts = Post.query.filter(Post.published == True, ~Post.id.in_(trending_ids)) \
            .order_by(Post.created_at.desc()) \
            .limit(6).all()
        
        # Get recent videos
        recent_videos = Video.query.filter_by(published=True) \
            .order_by(Video.created_at.desc()) \
            .limit(3).all()
        
        return render_template('index.html', 
                              trending_posts=trending_posts,
                              posts=recent_posts, 
                              videos=recent_videos)
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
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre.', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    try:
        # Get counts and recent items
        total_posts = Post.query.count()
        total_videos = Video.query.count()
        total_comments = Comment.query.count()
        total_views = db.session.query(func.sum(Post.views)).scalar() or 0
        total_views += db.session.query(func.sum(Video.views)).scalar() or 0
        
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        recent_videos = Video.query.order_by(Video.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html',
                              total_posts=total_posts,
                              total_videos=total_videos,
                              total_comments=total_comments,
                              total_views=total_views,
                              recent_posts=recent_posts,
                              recent_videos=recent_videos)
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {str(e)}")
        flash('Dashboard yüklenirken bir hata oluştu!', 'danger')
        return render_template('admin/dashboard.html',
                              total_posts=0,
                              total_videos=0,
                              total_comments=0,
                              total_views=0,
                              recent_posts=[],
                              recent_videos=[])

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        
        # Increment views
        post.views += 1
        db.session.commit()
        
        # Get approved comments for this post
        comments = Comment.query.filter_by(post_id=post_id, status='approved').all()
        
        return render_template('post.html', post=post, comments=comments)
    except Exception as e:
        app.logger.error(f"Post detail error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        
        name = request.form.get('name')
        email = request.form.get('email')
        content = request.form.get('content')
        
        if not name or not content:
            flash('İsim ve yorum alanları zorunludur.', 'danger')
            return redirect(url_for('post_detail', post_id=post_id))
        
        new_comment = Comment(
            name=name,
            email=email,
            content=content,
            post_id=post_id,
            status='pending'  # Start as pending for moderation
        )
        
        db.session.add(new_comment)
        db.session.commit()
        
        flash('Yorumunuz gönderildi ve onay bekliyor.', 'success')
        return redirect(url_for('post_detail', post_id=post_id))
    except Exception as e:
        app.logger.error(f"Add comment error: {str(e)}")
        flash('Yorumunuz eklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))

@app.route('/post/<int:post_id>/rate/<action>', methods=['POST'])
def rate_post(post_id, action):
    try:
        # Validate CSRF token
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            app.logger.warning(f"CSRF validation failed for rate_post attempt on post {post_id}")
            return jsonify({'success': False, 'message': 'Invalid security token.'}), 400
        
        if action not in ['like', 'dislike']:
            return jsonify({'success': False, 'message': 'Geçersiz işlem.'}), 400
        
        post = Post.query.get_or_404(post_id)
        
        if action == 'like':
            post.likes += 1
        else:
            post.dislikes += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'likes': post.likes,
            'dislikes': post.dislikes,
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
        search_query = request.args.get('search', '')
        
        if search_query:
            posts = Post.query.filter(
                Post.title.ilike(f'%{search_query}%') | 
                Post.content.ilike(f'%{search_query}%')
            ).order_by(Post.created_at.desc()).all()
        else:
            posts = Post.query.order_by(Post.created_at.desc()).all()
        
        return render_template('admin/posts.html', posts=posts, search_query=search_query)
    except Exception as e:
        app.logger.error(f"Admin posts error: {str(e)}")
        flash('Hikayeler yüklenirken bir hata oluştu!', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    try:
        categories = Category.query.all()
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            category_id = request.form.get('category_id')
            excerpt = request.form.get('excerpt')
            published = request.form.get('published') == 'on'
            featured = request.form.get('featured') == 'on'
            image = request.files.get('image')
            author = request.form.get('author')
            
            if not title or not content:
                flash('Başlık ve içerik alanları zorunludur.', 'danger')
                return render_template('admin/post_form.html', categories=categories)
            
            # Create new post
            new_post = Post(
                title=title,
                content=content,
                category_id=int(category_id) if category_id else None,
                excerpt=excerpt,
                published=published,
                featured=featured,
                author=author
            )
            
            # Handle image upload
            if image and image.filename:
                # Check if Supabase integration is available
                if supabase:
                    # Upload to Supabase Storage
                    image_url = upload_to_supabase(image, folder="posts")
                    if image_url:
                        new_post.image = image_url  # Store the full URL
                    else:
                        app.logger.warning("Supabase upload failed, falling back to local storage")
                        # Fall back to local storage if Supabase upload fails
                        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                        image_path = os.path.join('static', 'uploads', filename)
                        
                        # Ensure uploads directory exists
                        os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                        
                        # Save the image
                        image.save(image_path)
                        
                        # Resize image if needed
                        resize_image(image_path)
                        
                        new_post.image = filename  # Store just the filename
                else:
                    # Supabase integration not available, use local storage
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                    image_path = os.path.join('static', 'uploads', filename)
                    
                    # Ensure uploads directory exists
                    os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                    
                    # Save the image
                    image.save(image_path)
                    
                    # Resize image if needed
                    resize_image(image_path)
                    
                    new_post.image = filename  # Store just the filename
            
            # Add to database
            db.session.add(new_post)
            db.session.commit()
            
            flash('Hikaye başarıyla eklendi!', 'success')
            return redirect(url_for('admin_posts'))
        
        return render_template('admin/post_form.html', categories=categories)
    except Exception as e:
        app.logger.error(f"Admin new post error: {str(e)}")
        flash('Hikaye eklenirken bir hata oluştu!', 'danger')
        return render_template('admin/post_form.html', categories=categories)

@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        categories = Category.query.all()
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            category_id = request.form.get('category_id')
            excerpt = request.form.get('excerpt')
            published = request.form.get('published') == 'on'
            featured = request.form.get('featured') == 'on'
            image = request.files.get('image')
            remove_image = request.form.get('remove_image') == 'on'
            author = request.form.get('author')
            
            if not title or not content:
                flash('Başlık ve içerik alanları zorunludur.', 'danger')
                return render_template('admin/post_form.html', post=post, categories=categories)
            
            # Update post data
            post.title = title
            post.content = content
            post.category_id = int(category_id) if category_id else None
            post.excerpt = excerpt
            post.published = published
            post.featured = featured
            post.author = author
            
            # Handle image
            if remove_image and post.image:
                # Remove image reference
                post.image = None
            
            if image and image.filename:
                # Check if Supabase integration is available
                if supabase:
                    # Upload to Supabase Storage
                    image_url = upload_to_supabase(image, folder="posts")
                    if image_url:
                        post.image = image_url  # Store the full URL
                    else:
                        app.logger.warning("Supabase upload failed, falling back to local storage")
                        # Fall back to local storage if Supabase upload fails
                        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                        image_path = os.path.join('static', 'uploads', filename)
                        
                        # Ensure uploads directory exists
                        os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                        
                        # Save the image
                        image.save(image_path)
                        
                        # Resize image if needed
                        resize_image(image_path)
                        
                        post.image = filename  # Store just the filename
                else:
                    # Supabase integration not available, use local storage
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                    image_path = os.path.join('static', 'uploads', filename)
                    
                    # Ensure uploads directory exists
                    os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                    
                    # Save the image
                    image.save(image_path)
                    
                    # Resize image if needed
                    resize_image(image_path)
                    
                    post.image = filename  # Store just the filename
            
            # Save changes
            db.session.commit()
            
            flash('Hikaye başarıyla güncellendi!', 'success')
            return redirect(url_for('admin_posts'))
        
        return render_template('admin/post_form.html', post=post, categories=categories)
    except Exception as e:
        app.logger.error(f"Admin edit post error: {str(e)}")
        flash('Hikaye düzenlenirken bir hata oluştu!', 'danger')
        return redirect(url_for('admin_posts'))

@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        
        if post.image:
            # Try to remove the image file
            try:
                image_path = os.path.join('static', 'uploads', post.image)
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                app.logger.error(f"Error removing image: {str(e)}")
        
        # Delete the post (and associated comments via cascade)
        db.session.delete(post)
        db.session.commit()
        
        flash('Gönderi başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete post error: {str(e)}")
        flash('Gönderi silinirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_posts'))

@app.route('/admin/posts/<int:post_id>/view')
@login_required
def admin_view_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        comments = Comment.query.filter_by(post_id=post_id).all()
        
        return render_template('admin/view_post.html', post=post, comments=comments)
    except Exception as e:
        app.logger.error(f"View post error: {str(e)}")
        flash('Gönderi görüntülenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_posts'))

@app.route('/admin/categories')
@login_required
def admin_categories():
    try:
        categories = Category.query.all()
        
        # Add post and video counts to each category
        for category in categories:
            category.post_count = Post.query.filter_by(category_id=category.id).count()
            category.video_count = Video.query.filter_by(category_id=category.id).count()
            
        return render_template('admin/categories.html', categories=categories)
    except Exception as e:
        app.logger.error(f"Admin categories error: {str(e)}")
        flash('Kategoriler yüklenirken bir hata oluştu.', 'danger')
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
        
        # Check if category with same name or slug exists
        existing = Category.query.filter((Category.name == name) | (Category.slug == slug)).first()
        if existing:
            flash('Bu isim veya slug ile bir kategori zaten mevcut.', 'danger')
            return redirect(url_for('admin_categories'))
        
        # Create new category
        new_category = Category(name=name, slug=slug)
        db.session.add(new_category)
        db.session.commit()
        
        flash('Kategori başarıyla oluşturuldu.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"New category error: {str(e)}")
        flash('Kategori oluşturulurken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def admin_delete_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        
        # Update posts with this category to have no category
        Post.query.filter_by(category_id=category_id).update({Post.category_id: None})
        Video.query.filter_by(category_id=category_id).update({Video.category_id: None})
        
        # Delete the category
        db.session.delete(category)
        db.session.commit()
        
        flash('Kategori başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete category error: {str(e)}")
        flash('Kategori silinirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:category_id>/edit', methods=['POST'])
@login_required
def admin_edit_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        
        name = request.form.get('name')
        
        if not name:
            flash('Kategori adı gereklidir.', 'danger')
            return redirect(url_for('admin_categories'))
        
        # Check if category with same name exists (excluding this category)
        existing = Category.query.filter(Category.name == name, Category.id != category_id).first()
        if existing:
            flash('Bu isim ile bir kategori zaten mevcut.', 'danger')
            return redirect(url_for('admin_categories'))
        
        # Update category name
        category.name = name
        db.session.commit()
        
        flash('Kategori başarıyla güncellendi.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Edit category error: {str(e)}")
        flash('Kategori güncellenirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/comments')
@login_required
def admin_comments():
    try:
        comments = Comment.query.all()
        return render_template('admin/comments.html', comments=comments)
    except Exception as e:
        app.logger.error(f"Admin comments error: {str(e)}")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/comments/<int:comment_id>/approve', methods=['POST'])
@login_required
def approve_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        comment.status = 'approved'
        db.session.commit()
        flash(f'Yorum onaylandı.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Approve comment error: {str(e)}")
        flash('Yorum onaylanırken bir hata oluştu.', 'danger')
    return redirect(url_for('admin_comments'))

@app.route('/admin/comments/<int:comment_id>/reject', methods=['POST'])
@login_required
def reject_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        comment.status = 'rejected'
        db.session.commit()
        flash(f'Yorum reddedildi.', 'warning')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Reject comment error: {str(e)}")
        flash('Yorum reddedilirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin_comments'))

@app.route('/admin/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete comment error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/settings')
@login_required
def admin_settings():
    try:
        # Add debug output
        app.logger.info("Starting admin_settings route")
        
        # First, ensure the current admin user is also in admin_users table
        sync_admin_user(current_user)
        app.logger.info(f"Synced admin user: {current_user.username}")
        
        # Fetch admin users, email settings, and registration settings
        admins = AdminUser.query.order_by(AdminUser.username).all()
        app.logger.info(f"Found {len(admins)} admin users")
        
        email_settings = EmailSettings.query.first()
        app.logger.info(f"Email settings found: {email_settings is not None}")
        
        registration_settings = RegistrationSettings.query.first()
        app.logger.info(f"Registration settings found: {registration_settings is not None}")

        # If no email settings exist, create default settings
        if not email_settings:
            app.logger.info("Creating default email settings")
            email_settings = EmailSettings(
                smtp_server='',
                smtp_port=587,
                smtp_username='',
                smtp_password='',
                default_from_email=''
            )
            db.session.add(email_settings)
            # Don't commit here, commit at the end if needed

        # If no registration settings exist, create default settings
        if not registration_settings:
            app.logger.info("Creating default registration settings")
            registration_settings = RegistrationSettings(
                enable_registration=True,
                require_email_verification=True,
                allow_guest_posts=False,
                default_user_role='user'
            )
            db.session.add(registration_settings)

        # Commit if we created default settings
        if not EmailSettings.query.first() or not RegistrationSettings.query.first():
            db.session.commit()
            # Re-query after commit to get IDs if created
            email_settings = EmailSettings.query.first()
            registration_settings = RegistrationSettings.query.first()
            app.logger.info("Committed default settings")

        app.logger.info("Rendering admin/settings.html with all context variables")
        app.logger.info(f"Template variables: admins={len(admins)}, email_settings={email_settings is not None}, registration_settings={registration_settings is not None}")
        
        return render_template('admin/settings.html',
                              admins=admins,
                              email_settings=email_settings,
                              registration_settings=registration_settings)
    except Exception as e:
        db.session.rollback()  # Rollback in case of error during fetch/create
        app.logger.error(f"Admin settings error: {str(e)}")
        app.logger.error(f"Exception details: {e}", exc_info=True)
        flash('Ayarlar yüklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/change-password', methods=['POST'])
@login_required
def admin_change_password():
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Tüm alanları doldurun.', 'danger')
            return redirect(url_for('admin_settings'))
        
        if new_password != confirm_password:
            flash('Yeni şifreler eşleşmiyor.', 'danger')
            return redirect(url_for('admin_settings'))
        
        user = User.query.get(current_user.id)
        
        if not user or not user.check_password(current_password):
            flash('Mevcut şifre yanlış.', 'danger')
            return redirect(url_for('admin_settings'))
        
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Şifreniz başarıyla güncellendi.', 'success')
        return redirect(url_for('admin_settings'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Change password error: {str(e)}")
        flash('Şifre değiştirilirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_settings'))

@app.route('/admin/settings/add-admin', methods=['POST'])
@login_required
def admin_add_admin():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate inputs
        if not username or not email or not password:
            flash('Tüm alanları doldurun.', 'danger')
            return redirect(url_for('admin_settings'))
        
        # Check if username or email already exists
        if AdminUser.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten kullanılıyor.', 'danger')
            return redirect(url_for('admin_settings'))
        
        if AdminUser.query.filter_by(email=email).first():
            flash('Bu e-posta adresi zaten kullanılıyor.', 'danger')
            return redirect(url_for('admin_settings'))
        
        # Create new admin user
        new_admin = AdminUser(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(new_admin)
        db.session.commit()
        
        flash('Yeni yönetici başarıyla eklenmiştir.', 'success')
        return redirect(url_for('admin_settings'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Add admin error: {str(e)}")
        flash('Yönetici eklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_settings'))

@app.route('/admin/settings/delete-admin/<int:admin_id>', methods=['POST'])
@login_required
def admin_delete_admin(admin_id):
    try:
        admin = AdminUser.query.get_or_404(admin_id)
        
        # Prevent deletion of the current user
        if admin.username == current_user.username:
            return jsonify({'success': False, 'message': 'Kendinizi silemezsiniz.'})
        
        db.session.delete(admin)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete admin error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/settings/update-email', methods=['POST'])
@login_required
def admin_update_email_settings():
    try:
        smtp_server = request.form.get('smtp_server')
        smtp_port = request.form.get('smtp_port')
        smtp_username = request.form.get('smtp_username')
        smtp_password = request.form.get('smtp_password')
        default_from_email = request.form.get('default_from_email')
        
        # Validate inputs
        if not smtp_server or not smtp_port or not smtp_username or not smtp_password or not default_from_email:
            flash('Tüm alanları doldurun.', 'danger')
            return redirect(url_for('admin_settings'))
        
        # Get or create email settings
        email_settings = EmailSettings.query.first()
        if not email_settings:
            email_settings = EmailSettings()
            db.session.add(email_settings)
        
        # Update email settings
        email_settings.smtp_server = smtp_server
        email_settings.smtp_port = int(smtp_port)
        email_settings.smtp_username = smtp_username
        email_settings.smtp_password = smtp_password
        email_settings.default_from_email = default_from_email
        
        db.session.commit()
        
        flash('E-posta ayarları başarıyla güncellendi.', 'success')
        return redirect(url_for('admin_settings'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Update email settings error: {str(e)}")
        flash('E-posta ayarları güncellenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_settings'))

@app.route('/admin/settings/update-registration', methods=['POST'])
@login_required
def admin_update_registration_settings():
    try:
        enable_registration = 'enable_registration' in request.form
        require_email_verification = 'require_email_verification' in request.form
        allow_guest_posts = 'allow_guest_posts' in request.form
        default_user_role = request.form.get('default_user_role')
        
        # Get or create registration settings
        registration_settings = RegistrationSettings.query.first()
        if not registration_settings:
            registration_settings = RegistrationSettings()
            db.session.add(registration_settings)
        
        # Update registration settings
        registration_settings.enable_registration = enable_registration
        registration_settings.require_email_verification = require_email_verification
        registration_settings.allow_guest_posts = allow_guest_posts
        registration_settings.default_user_role = default_user_role
        
        db.session.commit()
        
        flash('Kayıt ayarları başarıyla güncellendi.', 'success')
        return redirect(url_for('admin_settings'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Update registration settings error: {str(e)}")
        flash('Kayıt ayarları güncellenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_settings'))

@app.route('/admin/videos')
@login_required
def admin_videos():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10 # Show 10 videos per page
        
        # Query videos with pagination
        pagination = Video.query.order_by(Video.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        videos = pagination.items
        
        # Pass categories for filtering (optional, but the template has the dropdown)
        categories = Category.query.all()
        
        return render_template('admin/videos.html', 
                              videos=videos,
                              categories=categories,
                              current_page=pagination.page,
                              total_pages=pagination.pages)
    except Exception as e:
        app.logger.error(f"Admin videos error: {str(e)}")
        flash('Videoları yüklerken bir hata oluştu!', 'danger')
        # Still render the template but with empty list and potentially no pagination
        return render_template('admin/videos.html', videos=[], categories=[], current_page=1, total_pages=1)

@app.route('/admin/new-video', methods=['GET', 'POST'])
@login_required
def admin_new_video():
    try:
        categories = Category.query.all()
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            url = request.form.get('url')
            thumbnail_file = request.files.get('thumbnail_file')
            
            # Safer category_id handling
            category_id_str = request.form.get('category_id')
            category_id = int(category_id_str) if category_id_str and category_id_str.isdigit() else None
            
            # If no category is selected, try to find and use the 'video' category
            if not category_id:
                video_category = Category.query.filter_by(slug='video').first()
                if video_category:
                    category_id = video_category.id
            
            # Validate required fields (optional but good practice)
            if not title or not url:
                flash('Başlık ve URL alanları zorunludur.', 'danger')
                return render_template('admin/new_video.html', categories=categories)
                
            # Basic URL validation
            if not url.startswith('http://') and not url.startswith('https://'):
                flash('Geçerli bir URL giriniz (http:// veya https:// ile başlamalı).', 'danger')
                return render_template('admin/new_video.html', categories=categories, title=title, description=description, url=url)
            
            thumbnail_url = None
            if thumbnail_file and thumbnail_file.filename:
                # Check if Supabase integration is available
                if supabase:
                    # Upload to Supabase Storage
                    thumbnail_url = upload_to_supabase(thumbnail_file, folder="video_thumbnails")
                    if not thumbnail_url:
                        app.logger.warning("Supabase upload failed, falling back to local storage")
                        # Fall back to local storage if Supabase upload fails
                        filename = secure_filename(f"video_thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{thumbnail_file.filename}")
                        image_path = os.path.join('static', 'uploads', filename)
                        
                        # Ensure uploads directory exists
                        os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                        
                        # Save the image
                        thumbnail_file.save(image_path)
                        
                        # Resize image if needed
                        resize_image(image_path)
                        
                        thumbnail_url = filename  # Store just the filename
                else:
                    # Supabase integration not available, use local storage
                    filename = secure_filename(f"video_thumb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{thumbnail_file.filename}")
                    image_path = os.path.join('static', 'uploads', filename)
                    
                    # Ensure uploads directory exists
                    os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                    
                    # Save the image
                    thumbnail_file.save(image_path)
                    
                    # Resize image if needed
                    resize_image(image_path)
                    
                    thumbnail_url = filename  # Store just the filename

            # Create new video
            new_video = Video(
                title=title,
                description=description,
                url=url,
                # Use the thumbnail URL (either from Supabase or local)
                thumbnail_url=thumbnail_url,
                category_id=category_id,
                published=True
            )
            
            db.session.add(new_video)
            db.session.commit()
            
            flash('Video başarıyla eklendi!', 'success')
            return redirect(url_for('admin_videos'))
        
        return render_template('admin/new_video.html', categories=categories)
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin new video error: {str(e)}")
        flash('Video eklenirken bir hata oluştu! Detaylar için logları kontrol edin.', 'danger')
        return redirect(url_for('admin_videos'))

@app.route('/admin/video/<int:video_id>/view')
@login_required
def admin_view_video(video_id):
    # Placeholder - Add logic to fetch and display video details
    video = Video.query.get_or_404(video_id)
    flash('Video görüntüleme işlevi henüz tamamlanmadı.', 'info')
    return render_template('admin/view_video.html', video=video) # Assuming view_video.html exists

@app.route('/admin/video/<int:video_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_video(video_id):
    # Placeholder - Add logic to fetch video and handle form submission for editing
    video = Video.query.get_or_404(video_id)
    categories = Category.query.all()
    if request.method == 'POST':
        # Placeholder for processing form data
        flash('Video düzenleme işlevi henüz tamamlanmadı.', 'info')
        return redirect(url_for('admin_videos'))
    return render_template('admin/edit_video.html', video=video, categories=categories) # Assuming edit_video.html exists

@app.route('/admin/video/<int:video_id>/delete', methods=['POST'])
@login_required
def admin_delete_video(video_id):
    try:
        video = Video.query.get_or_404(video_id)
        
        # If the video has a thumbnail, try to delete it
        if video.thumbnail_url:
            try:
                thumbnail_path = os.path.join('static', 'uploads', video.thumbnail_url)
                if os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
            except Exception as e:
                app.logger.error(f"Error removing thumbnail for video {video_id}: {str(e)}")
        
        # Delete any comments associated with this video (should be handled by cascade)
        video_title = video.title  # Store title before deletion
        
        # Delete the video
        db.session.delete(video)
        db.session.commit()
        
        flash(f'"{video_title}" videosu başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting video {video_id}: {str(e)}")
        flash('Video silinirken bir hata oluştu!', 'danger')
    
    return redirect(url_for('admin_videos'))

@app.route('/admin')
@login_required
def admin_index():
    return redirect(url_for('admin_dashboard'))

# Create a function to resize images to save space
def resize_image(image_path, max_size=(800, 800)):
    """Resize an image if it's larger than max_size"""
    try:
        img = Image.open(image_path)
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size)
            img.save(image_path)
    except Exception as e:
        app.logger.error(f"Error resizing image: {str(e)}")

# File upload route for CKEditor
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle file uploads from CKEditor"""
    try:
        f = request.files.get('upload')
        if not f:
            return jsonify({'error': {'message': 'No file provided'}})
        
        if f and f.filename:
            url = None
            
            # Check if Supabase integration is available
            if supabase:
                # Upload to Supabase Storage
                url = upload_to_supabase(f, folder="editor")
            
            # If Supabase upload failed or is not available, fall back to local storage
            if not url:
                # Generate secure filename
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.filename}")
                file_path = os.path.join('static', 'uploads', filename)
                
                # Ensure uploads directory exists
                os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                
                # Save the file
                f.save(file_path)
                
                # Resize image if it's too large
                resize_image(file_path)
                
                # Generate URL for CKEditor
                url = url_for('static', filename=f"uploads/{filename}")
            
            # Return success response
            return jsonify({
                'url': url,
                'uploaded': 1,
                'fileName': f.filename
            })
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'uploaded': 0,
            'error': {'message': 'Could not upload file. Please try again.'}
        })

# Data Storage Configuration (for migration)
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

POSTS_FILE = os.path.join(DATA_DIR, 'posts.json')
VIDEOS_FILE = os.path.join(DATA_DIR, 'videos.json')
CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')
COMMENTS_FILE = os.path.join(DATA_DIR, 'comments.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# File-based data helpers (kept for migration)
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

def initialize_database():
    """Initialize the database with default data if it's empty"""
    try:
        # Check if categories exist instead of just checking users
        if Category.query.count() == 0:
            app.logger.info("No categories found, creating default categories")
            
            # Create default categories
            categories = [
                Category(name='Öykü', slug='oyku'),
                Category(name='Roman', slug='roman'),
                Category(name='Şiir', slug='siir'),
                Category(name='Deneme', slug='deneme'),
                Category(name='İnceleme', slug='inceleme'),
                Category(name='Haber', slug='haber'),
                Category(name='Video', slug='video')
            ]
            db.session.add_all(categories)
            db.session.commit()
            
            # If we also need a default user
            if User.query.count() == 0:
                # Create default admin user
                admin = User(
                    username='admin',
                    password=generate_password_hash('admin')
                )
                db.session.add(admin)
                
                # Create a welcome post
                welcome_post = Post(
                    title='Hoş Geldiniz',
                    content='Hepsi Hikaye web sitesine hoş geldiniz. Bu bir örnek içeriktir.',
                    category=categories[0],  # Öykü
                    published=True,
                    featured=True
                )
                db.session.add(welcome_post)
                db.session.commit()
                
            app.logger.info("Database initialized with default data")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database initialization error: {str(e)}")

def migrate_from_json():
    """Migrate data from JSON files to the database"""
    try:
        # Only run migration if database is empty
        if User.query.count() > 0:
            app.logger.info("Database already contains data, skipping migration")
            return
            
        # Migrate categories
        categories_map = {}  # To store id mappings
        json_categories = load_data(CATEGORIES_FILE, [])
        for cat_data in json_categories:
            category = Category(
                id=cat_data.get('id'),
                name=cat_data.get('name'),
                slug=cat_data.get('slug')
            )
            db.session.add(category)
            categories_map[cat_data.get('id')] = category
        db.session.commit()
        app.logger.info(f"Migrated {len(json_categories)} categories")
        
        # Migrate posts
        posts_map = {}  # To store id mappings
        json_posts = load_data(POSTS_FILE, [])
        for post_data in json_posts:
            try:
                created_at = datetime.fromisoformat(post_data.get('created_at')) if post_data.get('created_at') else datetime.utcnow()
            except ValueError:
                created_at = datetime.utcnow()
                
            post = Post(
                id=post_data.get('id'),
                title=post_data.get('title'),
                content=post_data.get('content'),
                excerpt=post_data.get('excerpt'),
                image=post_data.get('image'),
                created_at=created_at,
                views=post_data.get('views', 0),
                likes=post_data.get('likes', 0),
                dislikes=post_data.get('dislikes', 0),
                published=post_data.get('published', True),
                featured=post_data.get('featured', False),
                category_id=post_data.get('category_id')
            )
            db.session.add(post)
            posts_map[post_data.get('id')] = post
        db.session.commit()
        app.logger.info(f"Migrated {len(json_posts)} posts")
        
        # Migrate videos
        videos_map = {}  # To store id mappings
        json_videos = load_data(VIDEOS_FILE, [])
        for video_data in json_videos:
            try:
                created_at = datetime.fromisoformat(video_data.get('created_at')) if video_data.get('created_at') else datetime.utcnow()
            except ValueError:
                created_at = datetime.utcnow()
                
            video = Video(
                id=video_data.get('id'),
                title=video_data.get('title'),
                description=video_data.get('description'),
                url=video_data.get('url'),
                thumbnail_url=video_data.get('thumbnail_url'),
                created_at=created_at,
                views=video_data.get('views', 0),
                published=video_data.get('published', True),
                category_id=video_data.get('category_id')
            )
            db.session.add(video)
            videos_map[video_data.get('id')] = video
        db.session.commit()
        app.logger.info(f"Migrated {len(json_videos)} videos")
        
        # Migrate comments
        json_comments = load_data(COMMENTS_FILE, [])
        for comment_data in json_comments:
            try:
                created_at = datetime.fromisoformat(comment_data.get('created_at')) if comment_data.get('created_at') else datetime.utcnow()
            except ValueError:
                created_at = datetime.utcnow()
                
            comment = Comment(
                id=comment_data.get('id'),
                content=comment_data.get('content'),
                name=comment_data.get('name', comment_data.get('author_name', 'Anonymous')),
                email=comment_data.get('email'),
                created_at=created_at,
                status=comment_data.get('status', 'approved'),
                post_id=comment_data.get('post_id'),
                video_id=comment_data.get('video_id')
            )
            db.session.add(comment)
        db.session.commit()
        app.logger.info(f"Migrated {len(json_comments)} comments")
        
        # Migrate users
        json_users = load_data(USERS_FILE, [])
        for user_data in json_users:
            user = User(
                id=user_data.get('id'),
                username=user_data.get('username'),
                password=user_data.get('password')  # Already hashed in JSON
            )
            db.session.add(user)
        db.session.commit()
        app.logger.info(f"Migrated {len(json_users)} users")
        
        app.logger.info("Migration from JSON completed successfully")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Migration error: {str(e)}")

@app.route('/search')
def search():
    try:
        query = request.args.get('search', '')
        
        if not query:
            return redirect(url_for('index'))
        
        # Use database queries instead of JSON files
        matching_posts = Post.query.filter(
            (Post.title.ilike(f'%{query}%') | Post.content.ilike(f'%{query}%')),
            Post.published == True
        ).order_by(Post.created_at.desc()).all()
        
        matching_videos = Video.query.filter(
            (Video.title.ilike(f'%{query}%') | Video.description.ilike(f'%{query}%')),
            Video.published == True
        ).order_by(Video.created_at.desc()).all()
        
        return render_template('search.html', 
                              posts=matching_posts, 
                              videos=matching_videos, 
                              query=query)
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/videos')
def videos():
    try:
        # Get all videos or filter by category if provided
        category_slug = request.args.get('category')
        
        if category_slug:
            category = Category.query.filter_by(slug=category_slug).first_or_404()
            videos_list = Video.query.filter_by(category_id=category.id, published=True).order_by(Video.created_at.desc()).all()
        else:
            videos_list = Video.query.filter_by(published=True).order_by(Video.created_at.desc()).all()
            
        return render_template('videos.html', videos=videos_list, category=category if category_slug else None)
    except Exception as e:
        app.logger.error(f"Videos list error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/manifesto')
def manifesto():
    return render_template('manifesto.html')

@app.context_processor
def inject_categories():
    """Make categories available to all templates"""
    try:
        categories = Category.query.all()
        return {'categories': categories}
    except Exception as e:
        app.logger.error(f"Context processor error: {str(e)}")
        return {'categories': []}

@app.route('/category/<slug>')
def category_posts(slug):
    try:
        category = Category.query.filter_by(slug=slug).first_or_404()
        
        # Check if this is the video category
        if slug == 'video':
            # For video category, fetch videos instead of posts
            videos = Video.query.filter_by(category_id=category.id, published=True).order_by(Video.created_at.desc()).all()
            return render_template('videos.html', videos=videos, category=category)
        else:
            # For other categories, fetch posts as before
            posts = Post.query.filter_by(category_id=category.id, published=True).order_by(Post.created_at.desc()).all()
            return render_template('category.html', category=category, posts=posts)
    except Exception as e:
        app.logger.error(f"Category posts error: {str(e)}")
        return render_template('errors/500.html')

def sync_admin_user(user):
    """Ensure the current admin user from User model is also in AdminUser model"""
    try:
        # Check if this user already exists in AdminUser
        admin_user = AdminUser.query.filter_by(username=user.username).first()
        
        if not admin_user:
            # Create a new entry in AdminUser for this user
            admin_user = AdminUser(
                username=user.username,
                email=f"{user.username}@hepsihikaye.net",  # Default email since User doesn't have email
                password_hash=user.password  # Copy the password hash
            )
            db.session.add(admin_user)
            db.session.commit()
            app.logger.info(f"Synced user {user.username} to admin_users table")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error syncing admin user: {str(e)}")

if __name__ == '__main__':
    # Create required directories
    for directory in ['static/uploads', 'static/logs']:
        if not os.path.exists(directory):
            os.makedirs(directory)
            app.logger.info(f'Created directory: {os.path.abspath(directory)}')
    
    # Initialize database
    with app.app_context():
        db.create_all()
        initialize_database()
        
    app.logger.info('Flask application started')
    # Run app on specified host and port, default 5000
    # Use 0.0.0.0 to be accessible on the network
    app.run(host=os.environ.get('FLASK_RUN_HOST', '127.0.0.1'), 
            port=int(os.environ.get('FLASK_RUN_PORT', 5000)), 
            debug=app.config['DEBUG'])

# --- MILESTONE MARKER ---
# Project: HepsiHikaye
# Milestone: First fully working version completed!
# Date: April 2, 2025
# Notes: Built with persistence and pair programming.
# ------------------------- 