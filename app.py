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
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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
            return None
        return url_for('serve_upload', filename=self.image_url)

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
    """Serve uploaded files consistently across environments"""
    try:
        # Log the request for debugging
        app.logger.info(f"Image request received for: {filename}")
        
        # Normalize filename - remove any leading slashes
        filename = filename.lstrip('/')
        
        # Determine file path based on environment
        if app.config['IS_PRODUCTION']:
            # In production environment
            app.logger.info(f"Serving file in PRODUCTION mode from {app.config['UPLOAD_FOLDER']}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        else:
            # In development environment
            upload_dir = os.path.join(app.static_folder, 'uploads')
            app.logger.info(f"Serving file in DEVELOPMENT mode from {upload_dir}")
            file_path = os.path.join(upload_dir, filename)
        
        # Check if the file exists
        if os.path.exists(file_path):
            app.logger.info(f"File exists at {file_path}")
        else:
            app.logger.warning(f"File NOT found at {file_path}, serving default image instead")
            return send_from_directory(app.static_folder, 'img/default-story.jpg')
            
        # Get the correct directory to serve from
        serve_dir = os.path.dirname(file_path)
        serve_filename = os.path.basename(file_path)
        
        return send_from_directory(serve_dir, serve_filename)
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {str(e)}")
        # Return a placeholder image instead of 404 for better user experience
        return send_from_directory(app.static_folder, 'img/default-story.jpg')

def get_db_connection():
    """Get database connection with retry logic and enhanced error handling"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Test the connection
            connection = db.engine.connect()
            app.logger.info("Successfully connected to the database")
            
            # Test a simple query using SQLAlchemy 2.0 syntax
            result = connection.execute(text("SELECT 1"))
            result.close()
            connection.close()
            
            return True
            
        except OperationalError as e:
            error_msg = str(e)
            app.logger.error(f"Database connection attempt {attempt + 1} failed:")
            app.logger.error(f"Error type: {type(e).__name__}")
            app.logger.error(f"Error message: {error_msg}")
            
            if "could not translate host name" in error_msg:
                app.logger.error("Hostname resolution failed. Please verify the database host is correct and accessible.")
            elif "connection refused" in error_msg:
                app.logger.error("Connection refused. Please verify the database is running and accepting connections.")
            elif "password authentication failed" in error_msg:
                app.logger.error("Authentication failed. Please verify your database credentials.")
            
            if attempt == max_retries - 1:
                app.logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise
                
            app.logger.warning(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
            
        except SQLAlchemyError as e:
            app.logger.error(f"SQLAlchemy error: {str(e)}")
            raise
            
        except Exception as e:
            app.logger.error(f"Unexpected error: {str(e)}")
            raise
            
    return False

@app.before_request
def check_db_connection():
    """Check database connection before each request with enhanced error handling"""
    if request.endpoint and 'static' in request.endpoint:
        return  # Skip check for static files
        
    try:
        get_db_connection()
    except OperationalError as e:
        app.logger.error(f"Database connection error: {str(e)}")
        if not request.is_xhr:  # Regular request
            flash('Veritabanı bağlantısı kurulamadı. Lütfen daha sonra tekrar deneyin.', 'error')
            return render_template('errors/db_error.html'), 503
        else:  # AJAX request
            return jsonify({'error': 'Database connection error'}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error checking database connection: {str(e)}")
        return "An unexpected error occurred", 500

def handle_db_error(func):
    """Decorator to handle database errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            app.logger.error(f"Database error in {func.__name__}: {str(e)}")
            db.session.rollback()
            flash('Veritabanı hatası oluştu. Lütfen daha sonra tekrar deneyin.', 'error')
            return redirect(url_for('index'))
    return wrapper

@app.route('/admin')
@login_required
@handle_db_error
def admin_index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template('admin/index.html', posts=posts, videos=videos)

@app.route('/admin/')
@login_required
def admin_index_slash():
    return redirect(url_for('admin_index'))

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
    port = int(os.environ.get('PORT', 10001))
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
    return {'upload_url': app.config['UPLOAD_URL']}

@app.route('/')
def index():
    """Home page showing featured and recent posts"""
    # Get trending/featured posts
    featured_posts = Post.get_trending_posts(12)
    
    # Get recent posts
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(12).all()
    
    # Get categories with post counts
    category_counts = db.session.query(
        Post.category, 
        func.count(Post.id).label('count')
    ).group_by(Post.category).all()
    
    # Format categories for the template
    categories = []
    category_dict = dict(CATEGORIES)
    for cat_key, count in category_counts:
        categories.append({
            'slug': cat_key,
            'name': category_dict.get(cat_key, cat_key.capitalize()),
            'count': count
        })
    
    # Get video content if any
    videos = Video.query.order_by(Video.created_at.desc()).limit(4).all()
    
    return render_template(
        'index.html', 
        featured_posts=featured_posts,
        recent_posts=recent_posts,
        categories=categories,
        videos=videos
    )

@app.route('/category/<category>')
def category(category):
    """Display posts for a specific category"""
    # Get posts for the category
    posts = Post.query.filter_by(category=category).order_by(Post.created_at.desc()).all()
    
    # Get categories with post counts for sidebar
    category_counts = db.session.query(
        Post.category, 
        func.count(Post.id).label('count')
    ).group_by(Post.category).all()
    
    # Format categories for the template
    categories = []
    category_dict = dict(CATEGORIES)
    for cat_key, count in category_counts:
        categories.append({
            'slug': cat_key,
            'name': category_dict.get(cat_key, cat_key.capitalize()),
            'count': count
        })
    
    # Get the display name for the category
    category_display = category_dict.get(category, category.capitalize())
    
    return render_template(
        'category.html',
        posts=posts,
        category=category,
        category_display=category_display,
        categories=categories
    )

@app.route('/post/<int:post_id>')
def post(post_id):
    """Display a single post"""
    post = Post.query.get_or_404(post_id)
    
    # Get categories with post counts for sidebar
    category_counts = db.session.query(
        Post.category, 
        func.count(Post.id).label('count')
    ).group_by(Post.category).all()
    
    # Format categories for the template
    categories = []
    category_dict = dict(CATEGORIES)
    for cat_key, count in category_counts:
        categories.append({
            'slug': cat_key,
            'name': category_dict.get(cat_key, cat_key.capitalize()),
            'count': count
        })
    
    return render_template(
        'post_detail.html',
        post=post,
        categories=categories
    )

@app.route('/author/<author>')
def author_posts(author):
    """Display posts by a specific author"""
    posts = Post.query.filter_by(author=author).order_by(Post.created_at.desc()).all()
    
    # Get categories with post counts for sidebar
    category_counts = db.session.query(
        Post.category, 
        func.count(Post.id).label('count')
    ).group_by(Post.category).all()
    
    # Format categories for the template
    categories = []
    category_dict = dict(CATEGORIES)
    for cat_key, count in category_counts:
        categories.append({
            'slug': cat_key,
            'name': category_dict.get(cat_key, cat_key.capitalize()),
            'count': count
        })
    
    return render_template(
        'author.html',
        author=author,
        posts=posts,
        categories=categories
    )

@app.route('/videos')
def videos():
    """Display video content"""
    all_videos = Video.query.order_by(Video.created_at.desc()).all()
    
    # Get categories with post counts for sidebar
    category_counts = db.session.query(
        Post.category, 
        func.count(Post.id).label('count')
    ).group_by(Post.category).all()
    
    # Format categories for the template
    categories = []
    category_dict = dict(CATEGORIES)
    for cat_key, count in category_counts:
        categories.append({
            'slug': cat_key,
            'name': category_dict.get(cat_key, cat_key.capitalize()),
            'count': count
        })
    
    return render_template(
        'videos.html',
        videos=all_videos,
        categories=categories
    )
