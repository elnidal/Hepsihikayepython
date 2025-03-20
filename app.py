from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm, CSRFProtect
from flask_ckeditor import CKEditor, CKEditorField
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired
from sqlalchemy import or_, func
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image, ImageDraw, ImageFont
import os
import time
import re
from datetime import datetime, timedelta, UTC
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import googleapiclient.discovery
import googleapiclient.errors
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from functools import wraps
import subprocess
from urllib.parse import urlparse
import sys
from sqlalchemy import text
from decorators import handle_db_error
from sqlalchemy.orm import joinedload

# Load environment variables from .env file in development mode
if os.path.exists('.env') and not os.environ.get('FLASK_ENV') == 'production':
    print("Loading environment variables from .env file")
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            os.environ[key] = value

# Custom exception for validation errors
class ValidationError(Exception):
    pass


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            app.logger.warning(f"Unauthenticated user attempted to access {request.path}")
            flash('Lütfen giriş yapın.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')

# Get database URL from environment variables with fallback to the new database
database_url = os.environ.get('DATABASE_URL', "postgresql://hepsihikaye_wyg3_user:JWWumjYdrR15YATOT4KJvsRz4XxkRxzX@dpg-cvanpdlumphs73ag0b80-a.oregon-postgres.render.com/hepsihikaye_wyg3")

# If the URL starts with 'postgres://', convert it to 'postgresql://' (needed for SQLAlchemy)
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add SSL configuration
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'sslmode': 'require'
    }
}

# Configure upload folder based on environment
is_production = os.environ.get('FLASK_ENV') == 'production'

if is_production:
    # In production, use a persistent directory for uploads
    # Note: On Render.com, /opt/render/project/src is persistent
    app.config['UPLOAD_FOLDER'] = '/opt/render/project/src/uploads'
    app.config['UPLOAD_URL'] = '/uploads'  # URL path for uploads in production
else:
    # In development, use static/uploads for file storage
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
    app.config['UPLOAD_URL'] = '/static/uploads'  # URL path for uploads in development

# Normalize upload path - ensure it doesn't have trailing slash
app.config['UPLOAD_FOLDER'] = app.config['UPLOAD_FOLDER'].rstrip('/')
app.config['UPLOAD_URL'] = app.config['UPLOAD_URL'].rstrip('/')

# Store current environment mode for easy reference
app.config['IS_PRODUCTION'] = is_production

# Ensure upload directory exists
try:
    # Fix any potential issues with the upload folder path
    upload_folder = app.config['UPLOAD_FOLDER']
    app.logger.info(f"Ensuring upload directory exists at: {upload_folder}")
    
    # Create the directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)
    
    # Verify the directory was created
    if os.path.exists(upload_folder) and os.path.isdir(upload_folder):
        app.logger.info(f"Upload directory confirmed at: {upload_folder}")
    else:
        app.logger.error(f"Failed to create upload directory at: {upload_folder}")
except Exception as e:
    app.logger.error(f"Error creating upload directory: {str(e)}")
    # Fallback to a directory we know will work
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.logger.info(f"Using fallback upload directory: {app.config['UPLOAD_FOLDER']}")

app.logger.info(f"Upload directory set to: {app.config['UPLOAD_FOLDER']}")
app.logger.info(f"Upload URL path set to: {app.config['UPLOAD_URL']}")
app.logger.info(f"Running in {'PRODUCTION' if is_production else 'DEVELOPMENT'} mode")

# Ensure default image directory exists
default_img_dir = os.path.join(app.static_folder, 'img')
os.makedirs(default_img_dir, exist_ok=True)

# Create default placeholder image if it doesn't exist
default_img_path = os.path.join(default_img_dir, 'default-story.jpg')
if not os.path.exists(default_img_path):
    try:
        # Create a simple placeholder image
        img = Image.new('RGB', (800, 600), color=(234, 234, 234))
        d = ImageDraw.Draw(img)
        
        # Add text
        d.rectangle([(200, 200), (600, 400)], fill=(245, 245, 245), outline=(200, 200, 200), width=2)
        d.text((400, 300), "HepsiHikaye", fill=(100, 100, 100), anchor="mm")
        
        # Save the image
        img.save(default_img_path)
        app.logger.info(f"Created default placeholder image at {default_img_path}")
    except Exception as e:
        app.logger.error(f"Failed to create default placeholder image: {str(e)}")

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# CKEditor configuration
app.config['CKEDITOR_ENABLE_CSRF'] = True
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'
app.config['CKEDITOR_HEIGHT'] = 400
app.config['CKEDITOR_PKG_TYPE'] = 'standard'
app.config['CKEDITOR_SERVE_LOCAL'] = False
app.config['CKEDITOR_CONFIG'] = {
    'toolbar': [
        ['Style', 'Format', 'Font', 'FontSize'],
        ['Bold', 'Italic', 'Underline', 'Strike'],
        ['TextColor', 'BGColor'],
        ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote'],
        ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
        ['Link', 'Unlink'],
        ['Image', 'Table', 'HorizontalRule', 'SpecialChar'],
        ['Undo', 'Redo'],
        ['RemoveFormat', 'Source'],
        ['Maximize']
    ],
    'filebrowserUploadUrl': '/upload',
    'filebrowserBrowseUrl': '/media-library',
    'image2_alignClasses': ['image-align-left', 'image-align-center', 'image-align-right'],
    'image2_disableResizer': False,
    'extraPlugins': 'image2,uploadimage',
    'removePlugins': 'image',
    'uploadUrl': '/upload'
}

# Configure logging
if not app.debug:
    # Prevent duplicate logging by removing existing handlers
    app.logger.handlers = []
    
    # Set up file handler
    file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    
    # Add a stream handler to output to stdout (for Render logs)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    stream_handler.setLevel(logging.DEBUG)  # Lower level for more details
    app.logger.addHandler(stream_handler)
    
    app.logger.setLevel(logging.DEBUG)  # Set to DEBUG to get more information
app.logger.info('HepsiHikaye startup')

app.logger.info(f'Upload directory: {app.config["UPLOAD_FOLDER"]}')
app.logger.info(f'Environment: {os.environ.get("FLASK_ENV", "Development")}')
app.logger.info(f'Static folder: {app.static_folder}')

@app.after_request
def after_request(response):
    if not os.environ.get('FLASK_ENV') == 'production':
        return response
        
    # Log only error responses (4xx and 5xx) in production
    # Exclude normal status codes like 206 (Partial Content) and 304 (Not Modified)
    if response.status_code >= 400:
        app.logger.warning(f'Request to {request.path} returned status code {response.status_code}')
    return response

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
ckeditor = CKEditor(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Lütfen giriş yapın!'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    """Load a user from the database based on their ID"""
    return User.query.get(int(user_id))

# YouTube API configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @staticmethod
    def get_by_username(username):
        return User.query.filter_by(username=username).first()

    def __repr__(self):
        return f'<User {self.username}>'

    def get_id(self):
        return str(self.id)

CATEGORIES = [
    ('öykü', 'Öykü'),
    ('roman', 'Roman'),
    ('şiir', 'Şiir'),
    ('deneme', 'Deneme'),
    ('inceleme', 'İnceleme'),
    ('haber', 'Haber'),
    ('video', 'Video'),
]

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # Store IP to prevent multiple votes
    is_like = db.Column(db.Boolean, nullable=False)  # True for like, False for dislike
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    is_approved = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45), nullable=True)
    
    @property
    def formatted_date(self):
        return self.created_at.strftime('%d.%m.%Y %H:%M')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    author = db.Column(db.String(100), index=True)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)
    likes = db.Column(db.Integer, default=0, index=True)
    dislikes = db.Column(db.Integer, default=0)
    ratings = db.relationship('Rating', backref='post', lazy=True)
    comments = db.relationship('Comment', backref='post', lazy=True, order_by="desc(Comment.created_at)")

    def get_category_display(self):
        """Get the display name for the category"""
        category_dict = dict(CATEGORIES)
        return category_dict.get(self.category, self.category.capitalize())

    def get_image_url(self):
        """Get the full URL for the post image"""
        if not self.image_url:
            return url_for('static', filename='uploads/default_post_image.png')
        
        # Check if the image_url already has the correct format
        if self.image_url.startswith('uploads/'):
            return url_for('static', filename=self.image_url)
        else:
            # Otherwise, prepend the uploads/ directory
            return url_for('static', filename=f'uploads/{self.image_url}')

    def update_rating_counts(self):
        """Update the likes and dislikes count for this post"""
        try:
            self.likes = Rating.query.filter_by(post_id=self.id, is_like=True).count()
            self.dislikes = Rating.query.filter_by(post_id=self.id, is_like=False).count()
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error updating rating counts: {str(e)}")
            db.session.rollback()

    def rating_score(self):
        """Calculate the rating score for sorting"""
        return self.likes - self.dislikes

    @property
    def rating_score(self):
        # Calculate score based on likes and recency
        now = datetime.now(UTC)
        
        # Make sure created_at has timezone info
        if self.created_at.tzinfo is None:
            # If created_at is naive, make it timezone-aware by assuming it's in UTC
            created_at_aware = self.created_at.replace(tzinfo=UTC)
        else:
            created_at_aware = self.created_at
            
        time_diff = now - created_at_aware
        hours_passed = time_diff.total_seconds() / 3600
        # Score decreases with time, increases with likes
        return (self.likes * 10) / (hours_passed + 1)

    @staticmethod
    def get_trending_posts(limit=5):
        posts = Post.query.all()
        # Sort posts by rating score
        sorted_posts = sorted(posts, key=lambda p: p.rating_score, reverse=True)
        return sorted_posts[:limit]

    @staticmethod
    def get_most_liked_posts(limit=5):
        return Post.query.order_by(Post.likes.desc()).limit(limit).all()

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    youtube_embed = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    @classmethod
    def get_value(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_value(cls, key, value):
        """Set a setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now(UTC)
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting

# Login Form
class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

# Post Form
class PostForm(FlaskForm):
    title = StringField('Başlık', validators=[DataRequired()])
    content = CKEditorField('İçerik', validators=[DataRequired()])
    category = SelectField('Kategori', choices=CATEGORIES, validators=[DataRequired()])
    author = StringField('Yazar')
    image = FileField('Kapak Resmi')
    submit = SubmitField('Kaydet')

# Video Form
class VideoForm(FlaskForm):
    title = StringField('Başlık', validators=[DataRequired()])
    youtube_embed = StringField('YouTube Embed ID', validators=[DataRequired()])
    submit = SubmitField('Kaydet')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(stream):
    """Validate that the file is actually an image and check its dimensions"""
    try:
        # Open the image using PIL
        img = Image.open(stream)
        
        # Check if it's actually an image
        img.verify()
        
        # Reopen the image after verify (verify closes the file)
        img = Image.open(stream)
        
        # Get image dimensions
        width, height = img.size
        
        # Check if dimensions are too large
        if width > 4096 or height > 4096:
            raise ValidationError("Image dimensions too large (max 4096x4096)")
            
        # Check format
        if img.format.lower() not in {'png', 'jpeg', 'jpg', 'gif'}:
            raise ValidationError("Invalid image format")
            
        return True
        
    except Exception as e:
        app.logger.error(f"Image validation error: {str(e)}")
        raise ValidationError("Invalid image file")

def resize_image(image_path, max_size=(800, 800)):
    """Resize image if it's larger than max_size while maintaining aspect ratio"""
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size, Image.LANCZOS)
        img.save(image_path)
    except Exception as e:
        app.logger.error(f"Error resizing image: {e}")
        raise

def fetch_youtube_videos(channel_identifier, max_results=10):
    """
    Fetch videos from a YouTube channel
    
    Args:
        channel_identifier (str): The YouTube channel ID or username (with or without @)
        max_results (int): Maximum number of videos to fetch
        
    Returns:
        list: List of video dictionaries with title, video_id, thumbnail_url, and published_at
    """
    # Get API key from database, fallback to environment variable
    api_key = Setting.get_value('youtube_api_key', YOUTUBE_API_KEY)
    
    if not api_key:
        app.logger.warning("YouTube API key is not set. Cannot fetch videos.")
        return []
        
    try:
        # Create YouTube API client
        youtube = googleapiclient.discovery.build(
            YOUTUBE_API_SERVICE_NAME, 
            YOUTUBE_API_VERSION, 
            developerKey=api_key
        )
        
        # Determine if we're using a channel ID or username
        channel_param = "id"
        
        # If it starts with @, it's a handle
        if channel_identifier.startswith('@'):
            channel_param = "forHandle"
        # If it doesn't start with UC, it might be a username
        elif not channel_identifier.startswith('UC'):
            channel_param = "forUsername"
            # Remove @ if it was included
            if channel_identifier.startswith('@'):
                channel_identifier = channel_identifier[1:]
        
        # Get channel uploads playlist ID
        channel_response = youtube.channels().list(
            part="contentDetails",
            **{channel_param: channel_identifier}
        ).execute()
        
        if not channel_response.get("items"):
            app.logger.warning(f"No channel found with identifier: {channel_identifier}")
            # Try as channel ID if we initially tried as username
            if channel_param == "forUsername":
                app.logger.info(f"Trying as channel ID instead: {channel_identifier}")
                channel_response = youtube.channels().list(
                    part="contentDetails",
                    id=channel_identifier
                ).execute()
                
                if not channel_response.get("items"):
                    app.logger.warning(f"No channel found with ID either: {channel_identifier}")
                    return []
            else:
                return []
            
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Get videos from uploads playlist
        playlist_response = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results
        ).execute()
        
        videos = []
        for item in playlist_response.get("items", []):
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            
            video = {
                "title": snippet["title"],
                "video_id": video_id,
                "thumbnail_url": snippet["thumbnails"]["high"]["url"],
                "published_at": snippet["publishedAt"],
                "embed_url": f"https://www.youtube.com/embed/{video_id}"
            }
            videos.append(video)
            
        return videos
        
    except googleapiclient.errors.HttpError as e:
        app.logger.error(f"YouTube API error: {e}")
        return []
    except Exception as e:
        app.logger.error(f"Error fetching YouTube videos: {e}")
        return []

def sync_youtube_videos(channel_identifier, max_results=10):
    """
    Sync videos from a YouTube channel to the database
    
    Args:
        channel_identifier (str): The YouTube channel ID or username (with or without @)
        max_results (int): Maximum number of videos to fetch
    """
    videos = fetch_youtube_videos(channel_identifier, max_results)
    
    videos_added = 0
    for video_data in videos:
        # Check if video already exists
        existing_video = Video.query.filter_by(youtube_embed=video_data["video_id"]).first()
        if not existing_video:
            # Create new video
            new_video = Video(
                title=video_data["title"],
                youtube_embed=video_data["video_id"],
                created_at=datetime.now(UTC)
            )
            db.session.add(new_video)
            videos_added += 1
    
    db.session.commit()
    return videos_added

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files from the static/uploads directory"""
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
        return redirect(url_for('static', filename='uploads/default_post_image.png'))

@app.route('/admin')
@login_required
def admin_index():
    """Admin ana sayfası"""
    try:
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        app.logger.error(f"Admin index error: {str(e)}")
        flash('Admin paneline erişimde bir hata oluştu.', 'error')
        return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin paneli ana sayfası"""
    try:
        # Son eklenen içerikleri getir
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
        recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(10).all()
        
        # İstatistikleri hesapla
        total_posts = Post.query.count()
        total_videos = Video.query.count()
        total_comments = Comment.query.count()
        total_views = sum(post.views for post in Post.query.all())
        
        return render_template('admin/dashboard.html',
                             posts=recent_posts,
                             videos=recent_videos,
                             comments=recent_comments,
                             total_posts=total_posts,
                             total_videos=total_videos,
                             total_comments=total_comments,
                             total_views=total_views)
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {str(e)}")
        flash('Admin paneli yüklenirken bir hata oluştu.', 'error')
        return redirect(url_for('index'))

def backup_database():
    """Create a backup of the PostgreSQL database"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            app.logger.error("DATABASE_URL not found in environment variables")
            return False
            
        # Parse database URL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'hepsihikaye_backup_{timestamp}.sql')
        
        # Extract connection details from DATABASE_URL
        url = urlparse(database_url)
        
        # Set PostgreSQL environment variables
        env = os.environ.copy()
        env['PGHOST'] = url.hostname
        env['PGPORT'] = str(url.port or 5432)
        env['PGUSER'] = url.username
        env['PGPASSWORD'] = url.password
        env['PGDATABASE'] = url.path[1:]
        
        # Run pg_dump
        cmd = ['pg_dump', '--clean', '--if-exists', '--format=p', '--file=' + backup_file]
        
        subprocess.run(cmd, env=env, check=True)
        
        app.logger.info(f"Database backup created successfully: {backup_file}")
        
        # Clean up old backups (keep last 5)
        backup_files = sorted([f for f in os.listdir(backup_dir) if f.startswith('hepsihikaye_backup_')])
        if len(backup_files) > 5:
            for old_file in backup_files[:-5]:
                os.remove(os.path.join(backup_dir, old_file))
                app.logger.info(f"Removed old backup: {old_file}")
        
        return True
        
    except Exception as e:
        app.logger.error(f"Backup failed: {str(e)}")
        return False

def init_db():
    """Initialize the database tables"""
    db.create_all()
    
    # Check if admin user exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create admin user with default password - change this in production!
        from werkzeug.security import generate_password_hash
        admin_user = User(username='admin', password=generate_password_hash('admin'))
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info("Admin user created successfully")
    else:
        app.logger.info("Admin user already exists")

def init_app():
    """Initialize the application (call this after app creation)"""
    with app.app_context():
        try:
            # Initialize database
            app.logger.info("Starting database initialization...")
            init_db()
            app.logger.info("Database initialized successfully")
            
            # Set up backup if in production
            if app.config['IS_PRODUCTION']:
                try:
                    app.logger.info("Attempting to create initial database backup...")
                    backup_database()
                    app.logger.info("Initial backup completed successfully")
                except Exception as e:
                    app.logger.error(f"Initial backup failed: {str(e)}")
                    app.logger.error(f"Error type: {type(e).__name__}")
                    import traceback
                    app.logger.error(f"Traceback: {traceback.format_exc()}")
                except Exception as e:
                    app.logger.error(f"Error initializing application: {str(e)}")
                    app.logger.error(f"Error type: {type(e).__name__}")
                    import traceback
                    app.logger.error(f"Traceback: {traceback.format_exc()}")
                    # Don't raise the error - log it and continue
                    # This prevents the application from failing to start

# Call the initialization function immediately if this is the main module
if __name__ == '__main__':
    # Initialize the app
    init_app()
    
    # Then start the server
    port = int(os.environ.get('PORT', 5001))
    app.debug = True
    app.run(host='0.0.0.0', port=port)

@app.route('/test-image')
def test_image_page():
    """Show a test page for debugging image display issues"""
    return render_template('test_image.html')

@app.route('/image-diagnostics')
@login_required
def image_diagnostics():
    """Admin page for diagnosing image issues"""
    # Get posts with images
    posts_with_images = Post.query.filter(Post.image_url.isnot(None)).order_by(Post.created_at.desc()).limit(10).all()
    
    # Get the upload folder configuration
    upload_info = {
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'upload_url': app.config['UPLOAD_URL'],
        'is_production': app.config['IS_PRODUCTION'],
        'static_folder': app.static_folder
    }
    
    # Get a list of files in the upload folder
    upload_files = []
    try:
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            upload_files = os.listdir(app.config['UPLOAD_FOLDER'])
    except Exception as e:
        app.logger.error(f"Error listing files in upload directory: {str(e)}")
    
    return render_template('admin/image_diagnostics.html', 
                          posts=posts_with_images, 
                          upload_info=upload_info,
                          upload_files=upload_files)

@app.context_processor
def inject_upload_url():
    """Make upload URL available to all templates"""
    try:
        app.logger.info(f"Injecting upload_url: {app.config['UPLOAD_URL']}")
        
        # Fix any potential formatting issues with the upload URL
        upload_url = app.config['UPLOAD_URL'].rstrip('/')
        
        # Ensure there's always a leading slash
        if not upload_url.startswith('/'):
            upload_url = '/' + upload_url
            
        app.logger.info(f"Final upload_url being provided to templates: {upload_url}")
        return {'upload_url': upload_url}
    except Exception as e:
        # Log any errors but return a default value
        app.logger.error(f"Error injecting upload_url: {str(e)}")
        # Default to /static/uploads if there's an error
        return {'upload_url': '/static/uploads'}

@app.context_processor
def inject_categories():
    """Make categories available to all templates"""
    try:
        app.logger.info("Injecting categories for template")
        
        # Get all defined categories from the global CATEGORIES list
        all_categories = []
        category_dict = dict(CATEGORIES)
        
        # Always include all defined categories, even if they have no posts
        for cat_key, cat_name in CATEGORIES:
            count = 0
            try:
                # Check if there are posts in this category
                count = Post.query.filter_by(category=cat_key).count()
            except Exception as e:
                # If there's a database error, just use 0
                app.logger.error(f"Error counting posts for category {cat_key}: {str(e)}")
                pass
                
            all_categories.append({
                'slug': cat_key,
                'name': cat_name,
                'count': count
            })
                
        app.logger.info(f"Returning {len(all_categories)} categories to template")
        return {'categories': all_categories}
        
    except Exception as e:
        # Log any other errors but don't crash - return empty categories
        app.logger.error(f"Unexpected error injecting categories: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Always return a valid list, even if empty
        return {'categories': []}

@app.route('/')
def index():
    """Home page showing featured and recent posts"""
    try:
        # Get trending/featured posts
        featured_posts = Post.get_trending_posts(12)
        
        # Get recent posts
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(12).all()
        
        # Get most liked posts
        most_liked_posts = Post.get_most_liked_posts(5)
        
        # Get video content if any
        videos = Video.query.order_by(Video.created_at.desc()).limit(4).all()
        
        return render_template(
            'index.html', 
            featured_posts=featured_posts,
            recent_posts=recent_posts,
            most_liked_posts=most_liked_posts,
            videos=videos
        )
    except Exception as e:
        # Log the detailed error
        app.logger.error(f"Error displaying index: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Re-raise to be caught by the error handler
        raise

@app.route('/category/<category>')
def category(category):
    """Display posts for a specific category"""
    try:
        # Get posts for the category
        posts = Post.query.filter_by(category=category).order_by(Post.created_at.desc()).all()
        
        # Get the display name for the category
        category_dict = dict(CATEGORIES)
        category_display = category_dict.get(category, category.capitalize())
        
        return render_template(
            'category.html',
            posts=posts, 
            category=category, 
            category_display=category_display
        )
    except Exception as e:
        # Log the detailed error
        app.logger.error(f"Error displaying category {category}: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Re-raise to be caught by the error handler
        raise

@app.route('/post/<int:post_id>')
def post(post_id):
    """Display a single post"""
    try:
        # Get the post or return 404
        post = Post.query.get_or_404(post_id)
        
        # Find related posts
        related_posts = Post.query.filter(
            Post.category == post.category,
            Post.id != post.id
        ).order_by(Post.created_at.desc()).limit(4).all()
        
        # Track page view for analytics (optional)
        app.logger.info(f"Post {post_id} viewed: {post.title}")
        
        return render_template(
            'post_detail.html',
            post=post,
            related_posts=related_posts
        )
    except Exception as e:
        # Log the detailed error
        app.logger.error(f"Error displaying post {post_id}: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Re-raise to be caught by the error handler
        raise

@app.route('/author/<author>')
def author_posts(author):
    """Display posts by a specific author"""
    try:
        # Get posts for the author
        posts = Post.query.filter_by(author=author).order_by(Post.created_at.desc()).all()
        
        return render_template(
            'author.html',
            author=author,
            posts=posts
        )
    except Exception as e:
        # Log the detailed error
        app.logger.error(f"Error displaying author {author}: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Re-raise to be caught by the error handler
        raise

@app.route('/videos')
def videos():
    """Display video content"""
    try:
        # Get all videos ordered by creation date
        all_videos = Video.query.order_by(Video.created_at.desc()).all()
        
        return render_template(
            'videos.html',
            videos=all_videos
        )
    except Exception as e:
        # Log the detailed error
        app.logger.error(f"Error displaying videos: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Re-raise to be caught by the error handler
        raise

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin giriş sayfası"""
    try:
        if current_user.is_authenticated:
            return redirect(url_for('admin_dashboard'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember', False)
            
            if not username or not password:
                flash('Lütfen kullanıcı adı ve şifrenizi girin.', 'error')
                return render_template('admin/login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('admin_dashboard')
                return redirect(next_page)
            else:
                flash('Geçersiz kullanıcı adı veya şifre.', 'error')
                
        return render_template('admin/login.html')
    except Exception as e:
        app.logger.error(f"Login error: {str(e)}")
        flash('Giriş yapılırken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'error')
        return render_template('admin/login.html')

@app.route('/logout')
@login_required
def logout():
    """Çıkış yap"""
    try:
        logout_user()
        flash('Başarıyla çıkış yaptınız.', 'success')
        return redirect(url_for('admin_login'))
    except Exception as e:
        app.logger.error(f"Logout error: {str(e)}")
        flash('Çıkış yapılırken bir hata oluştu.', 'error')
        return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors with detailed logging"""
    app.logger.error(f"500 error: {request.path}")
    
    # Log the exception if it exists
    if hasattr(error, 'original_exception'):
        original = error.original_exception
        app.logger.error(f"Original exception: {str(original)}")
        app.logger.error(f"Type: {type(original).__name__}")
        
        import traceback
        tb = traceback.format_exception(type(original), original, original.__traceback__)
        app.logger.error(f"Traceback: {''.join(tb)}")
    
    return render_template('errors/500.html'), 500

@app.errorhandler(Exception)
def handle_unhandled_exception(error):
    """Global exception handler for unhandled exceptions"""
    app.logger.error(f"Unhandled exception: {str(error)}")
    app.logger.error(f"Type: {type(error).__name__}")
    
    import traceback
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    app.logger.error(f"Traceback: {''.join(tb)}")
    
    return render_template('errors/500.html'), 500

@app.route('/check-health')
def health_check():
    """Simple health check endpoint for monitoring"""
    try:
        # Test database connection
        if get_db_connection():
            return jsonify({
                'status': 'ok',
                'db_connection': 'ok',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'warning',
                'db_connection': 'failed',
                'timestamp': datetime.now().isoformat()
            }), 500
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle file uploads from CKEditor"""
    try:
        f = request.files.get('upload')
        if f and allowed_file(f.filename):
            # Validate the file
            f.stream.seek(0)
            validate_image(f.stream)
            f.stream.seek(0)
            
            # Save the file
            filename = secure_filename(f.filename)
            timestamp = int(time.time())
            filename = f"{timestamp}_{filename}"
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(file_path)
            
            # Resize the image if needed
            resize_image(file_path)
            
            # Get the URL path
            if app.config['IS_PRODUCTION']:
                url = f"{app.config['UPLOAD_URL']}/{filename}"
            else:
                url = url_for('static', filename=f"uploads/{filename}")
            
            return jsonify({
                'uploaded': 1,
                'fileName': filename,
                'url': url
            })
        else:
            raise ValidationError('Invalid file type or no file provided')
    except ValidationError as e:
        app.logger.error(f"Upload validation error: {str(e)}")
        return jsonify({
            'uploaded': 0,
            'error': {
                'message': str(e)
            }
        })
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'uploaded': 0,
            'error': {
                'message': 'Dosya yüklenirken bir hata oluştu.'
            }
        })

@app.route('/media-library')
@login_required
def media_library():
    """Browse media files for CKEditor"""
    try:
        # List files in upload directory
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(filename):
                # Get file path and URL
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if app.config['IS_PRODUCTION']:
                    url = f"{app.config['UPLOAD_URL']}/{filename}"
                else:
                    url = url_for('static', filename=f"uploads/{filename}")
                
                # Get file info
                stats = os.stat(file_path)
                size_kb = stats.st_size / 1024
                modified = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                files.append({
                    'name': filename,
                    'url': url,
                    'size': f"{size_kb:.1f} KB",
                    'modified': modified
                })
        
        return render_template('admin/media_library.html', files=files)
    except Exception as e:
        app.logger.error(f"Media library error: {str(e)}")
        flash('Medya kütüphanesini görüntülerken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    """Add a comment to a post"""
    try:
        # Get the post or return 404
        post = Post.query.get_or_404(post_id)
        
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        content = request.form.get('content')
        
        # Validate inputs
        if not name or not email or not content:
            flash('Lütfen tüm alanları doldurun.', 'danger')
            return redirect(url_for('post', post_id=post_id))
        
        # Create and save the comment
        comment = Comment(
            post_id=post_id,
            name=name,
            email=email,
            content=content,
            ip_address=request.remote_addr,
            is_approved=False  # Comments require approval by default
        )
        
        db.session.add(comment)
        db.session.commit()
        
        # Show success message
        flash('Yorumunuz başarıyla gönderildi. Onaylandıktan sonra görüntülenecektir.', 'success')
        
        return redirect(url_for('post', post_id=post_id))
    except Exception as e:
        # Log the detailed error
        app.logger.error(f"Error adding comment to post {post_id}: {str(e)}")
        app.logger.error(f"Error type: {type(e).__name__}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        db.session.rollback()
        flash('Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz.', 'danger')
        return redirect(url_for('post', post_id=post_id))

@app.route('/admin/comments')
@login_required
def admin_comments():
    """Manage comments"""
    try:
        # Get comments with basic error handling
        comments = []
        
        try:
            # Get all comments
            comments = Comment.query.order_by(Comment.created_at.desc()).all()
            app.logger.info(f"Retrieved {len(comments)} comments for admin panel")
        except Exception as e:
            app.logger.error(f"Error retrieving comments: {str(e)}")
            flash('Yorumlar yüklenirken bir hata oluştu.', 'warning')
        
        return render_template('admin/comments.html', comments=comments, active_page='comments')
    except Exception as e:
        app.logger.error(f"Unhandled error in admin_comments: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash('Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz.', 'danger')
        return render_template('errors/500.html'), 500

@app.route('/admin/comment/<int:comment_id>/approve', methods=['POST'])
@login_required
def admin_approve_comment(comment_id):
    """Approve a comment"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        comment.is_approved = True
        db.session.commit()
        app.logger.info(f"Approved comment ID {comment_id}")
        flash('Yorum onaylandı.', 'success')
        return redirect(url_for('admin_comments'))
    except Exception as e:
        app.logger.error(f"Error approving comment: {str(e)}")
        flash('Yorum onaylanırken bir hata oluştu.', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/comment/<int:comment_id>/spam', methods=['POST'])
@login_required
def admin_spam_comment(comment_id):
    """Mark a comment as spam"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        comment.status = 'spam'
        
        try:
            db.session.commit()
            app.logger.info(f"Comment {comment_id} marked as spam by admin")
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error marking comment {comment_id} as spam: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    except Exception as e:
        app.logger.error(f"Unhandled error in admin_spam_comment: {str(e)}")
        return jsonify({'success': False, 'message': 'Bir hata oluştu.'}), 500

@app.route('/admin/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def admin_delete_comment(comment_id):
    """Delete a comment"""
    try:
        comment = Comment.query.get_or_404(comment_id)
        
        try:
            db.session.delete(comment)
            db.session.commit()
            app.logger.info(f"Comment {comment_id} deleted by admin")
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error deleting comment {comment_id}: {str(e)}")
            return jsonify({'success': False, 'message': str(e)})
    except Exception as e:
        app.logger.error(f"Unhandled error in admin_delete_comment: {str(e)}")
        return jsonify({'success': False, 'message': 'Bir hata oluştu.'}), 500

@app.route('/post/<int:post_id>/rate/<action>', methods=['POST'])
def rate_post(post_id, action):
    """Handle post rating (like/dislike)"""
    try:
        # Get the post or return 404
        post = Post.query.get_or_404(post_id)
        
        # Validate action
        if action not in ['like', 'dislike']:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
        # Get IP address for tracking votes
        ip_address = request.remote_addr
        
        # Check if the user has already rated this post
        existing_rating = Rating.query.filter_by(
            post_id=post_id,
            ip_address=ip_address
        ).first()
        
        is_like = action == 'like'
        
        if existing_rating:
            # If rating exists and is the same as the current action, remove it (toggle)
            if existing_rating.is_like == is_like:
                db.session.delete(existing_rating)
                message = 'Oyunuz kaldırıldı.'
            else:
                # Update existing rating
                existing_rating.is_like = is_like
                message = 'Oyunuz güncellendi.'
        else:
            # Create new rating
            rating = Rating(
                post_id=post_id,
                ip_address=ip_address,
                is_like=is_like
            )
            db.session.add(rating)
            message = 'Oyunuz kaydedildi.'
        
        # Commit changes
        db.session.commit()
        
        # Update post rating counts
        post.update_rating_counts()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'likes': post.likes,
            'dislikes': post.dislikes
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error rating post {post_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz.'}), 500

@app.route('/admin/new_post', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    """Create a new post"""
    app.logger.info("Entering admin_new_post route")
    form = PostForm()
    
    if form.validate_on_submit():
        try:
            title = form.title.data
            content = form.content.data
            category = form.category.data
            author = form.author.data or current_user.username
            
            # Handle image upload
            image_url = None
            if form.image.data:
                try:
                    image = form.image.data
                    if image and allowed_file(image.filename):
                        # Secure the filename
                        filename = secure_filename(image.filename)
                        
                        # Add a timestamp to avoid filename collisions
                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        
                        # Save the file
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        image.save(image_path)
                        
                        # Resize the image
                        resize_image(image_path)
                        
                        # Set the URL for the database
                        image_url = os.path.join(app.config['UPLOAD_URL'], filename)
                        app.logger.info(f"Image saved to {image_path}, URL: {image_url}")
                except Exception as e:
                    app.logger.error(f"Error uploading image: {str(e)}")
                    flash('Resim yüklenirken bir hata oluştu.', 'danger')
            
            # Create post
            post = Post(title=title, content=content, category=category, author=author, image_url=image_url)
            db.session.add(post)
            db.session.commit()
            
            app.logger.info(f"New post created: {title}")
            flash('Yazı başarıyla oluşturuldu.', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating post: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
            flash('Yazı oluşturulurken bir hata oluştu.', 'danger')
    
    return render_template('admin/new_post.html', form=form, active_page='new_post')

@app.route('/admin/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Edit an existing post"""
    app.logger.info(f"Entering edit_post route for post_id: {post_id}")
    post = Post.query.get_or_404(post_id)
    form = PostForm(obj=post)
    
    if form.validate_on_submit():
        try:
            # Update post from form data
            post.title = form.title.data
            post.content = form.content.data
            post.category = form.category.data
            post.author = form.author.data or post.author
            
            # Handle image upload if new image is provided
            if form.image.data:
                try:
                    image = form.image.data
                    if image and allowed_file(image.filename):
                        # Secure the filename
                        filename = secure_filename(image.filename)
                        
                        # Add a timestamp to avoid filename collisions
                        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                        filename = f"{timestamp}_{filename}"
                        
                        # Save the file
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        image.save(image_path)
                        
                        # Resize the image
                        resize_image(image_path)
                        
                        # Set the URL for the database
                        post.image_url = os.path.join(app.config['UPLOAD_URL'], filename)
                        app.logger.info(f"Image saved to {image_path}, URL: {post.image_url}")
                except Exception as e:
                    app.logger.error(f"Error uploading image: {str(e)}")
                    flash('Resim yüklenirken bir hata oluştu.', 'danger')
            
            # Save the changes
            db.session.commit()
            app.logger.info(f"Post {post_id} updated successfully")
            flash('Yazı başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating post: {str(e)}")
            flash('Yazı güncellenirken bir hata oluştu.', 'danger')
    
    return render_template('admin/edit_post.html', form=form, post=post, active_page='edit_post')

@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error deleting post {post_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/video/<int:video_id>/delete', methods=['POST'])
@login_required
def delete_video(video_id):
    try:
        video = Video.query.get_or_404(video_id)
        db.session.delete(video)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error deleting video {video_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/sync-youtube', methods=['GET', 'POST'])
@login_required
def sync_youtube():
    """Synchronize videos from YouTube"""
    if request.method == 'POST':
        channel_id = request.form.get('channel_id')
        max_results = int(request.form.get('max_results', 10))
        
        if not channel_id:
            flash('Lütfen bir YouTube kanal kimliği girin', 'danger')
            return redirect(url_for('sync_youtube'))
        
        try:
            videos_added = sync_youtube_videos(channel_id, max_results)
            flash(f'{videos_added} video başarıyla eklendi!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            app.logger.error(f"Error syncing YouTube videos: {str(e)}")
            flash(f'Videolar senkronize edilirken bir hata oluştu: {str(e)}', 'danger')
    
    # Get YouTube settings from database
    youtube_channel_id = Setting.get_value('youtube_channel_id', '')
    youtube_api_key = Setting.get_value('youtube_api_key', YOUTUBE_API_KEY)
    
    return render_template(
        'admin/sync_youtube.html',
        youtube_channel_id=youtube_channel_id,
        youtube_api_key=youtube_api_key
    )

@app.route('/admin/new_video', methods=['GET', 'POST'])
@login_required
def admin_new_video():
    """Add a new video manually"""
    app.logger.info("Entering admin_new_video route")
    form = VideoForm()
    
    if form.validate_on_submit():
        try:
            # Create new video
            title = form.title.data
            youtube_embed = form.youtube_embed.data
            
            # Extract just the video ID if full URLs are provided
            if '/' in youtube_embed:
                # Handle various YouTube URL formats
                if 'youtu.be/' in youtube_embed:
                    youtube_embed = youtube_embed.split('youtu.be/')[1].split('?')[0]
                elif 'youtube.com/watch' in youtube_embed:
                    youtube_embed = youtube_embed.split('v=')[1].split('&')[0]
                elif 'youtube.com/embed/' in youtube_embed:
                    youtube_embed = youtube_embed.split('embed/')[1].split('?')[0]
            
            video = Video(title=title, youtube_embed=youtube_embed)
            db.session.add(video)
            db.session.commit()
            
            app.logger.info(f"Created new video: {title} with YouTube ID: {youtube_embed}")
            flash('Video başarıyla eklendi.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding video: {str(e)}")
            flash('Video eklenirken bir hata oluştu.', 'danger')
    
    return render_template('admin/new_video.html', form=form, active_page='new_video')

@app.route('/admin/youtube_sync', methods=['GET', 'POST'])
@login_required
def admin_youtube_sync():
    """YouTube Video Sync Page"""
    try:
        form = YoutubeSyncForm()
        sync_results = None
        
        if form.validate_on_submit():
            try:
                channel_id = form.channel_id.data
                max_results = form.max_results.data
                
                # Call the sync function
                sync_results = sync_youtube_videos(channel_id, max_results)
                
                if sync_results['success']:
                    flash(f"Senkronizasyon başarılı: {sync_results['videos_added']} video eklendi.", 'success')
                else:
                    flash(f"Senkronizasyon hatası: {sync_results['error']}", 'danger')
            except Exception as e:
                app.logger.error(f"YouTube sync error: {str(e)}")
                flash(f"Video senkronizasyonu sırasında bir hata oluştu: {str(e)}", 'danger')
        
        return render_template('admin/youtube_sync.html', form=form, sync_results=sync_results, active_page='youtube_sync')
    except Exception as e:
        app.logger.error(f"Unhandled error in admin_youtube_sync: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash('Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz.', 'danger')
        return render_template('errors/500.html'), 500

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    """Admin settings page"""
    try:
        # Create form instances
        form = SiteSettingsForm()
        social_form = SocialMediaForm()
        api_form = APISettingsForm()
        password_form = ChangePasswordForm()
        
        # Get current settings from db or use defaults
        try:
            settings = Settings.query.first()
            if settings:
                form.site_title.data = settings.site_title
                form.site_description.data = settings.site_description
                form.contact_email.data = settings.contact_email
                form.posts_per_page.data = settings.posts_per_page
                form.comments_enabled.data = settings.comments_enabled
                form.auto_approve_comments.data = settings.auto_approve_comments
                
                social_form.facebook_url.data = settings.facebook_url
                social_form.twitter_url.data = settings.twitter_url
                social_form.instagram_url.data = settings.instagram_url
                social_form.youtube_url.data = settings.youtube_url
                
                api_form.youtube_api_key.data = settings.youtube_api_key
        except Exception as e:
            app.logger.error(f"Error retrieving settings: {str(e)}")
            flash('Ayarlar yüklenirken bir hata oluştu.', 'warning')
        
        return render_template('admin/settings.html', 
                               form=form, 
                               social_form=social_form, 
                               api_form=api_form, 
                               password_form=password_form,
                               active_page='settings')
    except Exception as e:
        app.logger.error(f"Unhandled error in admin_settings: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash('Bir hata oluştu. Lütfen daha sonra tekrar deneyiniz.', 'danger')
        return render_template('errors/500.html'), 500
