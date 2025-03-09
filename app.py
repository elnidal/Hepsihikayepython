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
from PIL import Image
import os
import time
import re
from datetime import datetime, timedelta, UTC
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import googleapiclient.discovery
import googleapiclient.errors

# Custom exception for validation errors
class ValidationError(Exception):
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("blog.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder based on environment
if os.environ.get('FLASK_ENV') == 'production':
    # In production, use a persistent directory for uploads
    # Note: On Render.com, /opt/render/project/src is persistent
    app.config['UPLOAD_FOLDER'] = '/opt/render/project/src/uploads'
    app.config['UPLOAD_URL'] = '/uploads'  # URL path for uploads in production
else:
    # In development, use static/uploads for file storage
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
    app.config['UPLOAD_URL'] = '/static/uploads'  # URL path for uploads in development

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.logger.info(f"Upload directory set to: {app.config['UPLOAD_FOLDER']}")

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
logging.basicConfig(level=logging.INFO)
if os.environ.get('FLASK_ENV') == 'production':
    # In production, log to stdout for Render.com
    handler = logging.StreamHandler()
else:
    # In development, log to a file
    if not os.path.exists('logs'):
        os.makedirs('logs')
    handler = RotatingFileHandler('logs/hepsihikaye.log', maxBytes=10240, backupCount=10)

handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
app.logger.info('HepsiHikaye startup')

# Log important configuration
app.logger.info(f'Upload directory: {app.config["UPLOAD_FOLDER"]}')
app.logger.info(f'Environment: {os.environ.get("FLASK_ENV", "Development")}')
app.logger.info(f'Static folder: {app.static_folder}')

@app.after_request
def after_request(response):
    if not os.environ.get('FLASK_ENV') == 'production':
        return response
        
    # Log non-successful responses in production
    if response.status_code != 200:
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
    """Serve uploaded files"""
    try:
        if os.environ.get('FLASK_ENV') == 'production':
            # In production, serve from the /tmp/uploads directory
            app.logger.info(f"Serving file {filename} from {app.config['UPLOAD_FOLDER']}")
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        else:
            # In development, serve from the static/uploads directory
            app.logger.info(f"Serving file {filename} from {os.path.join(app.static_folder, 'uploads')}")
            return send_from_directory(os.path.join(app.static_folder, 'uploads'), filename)
    except Exception as e:
        app.logger.error(f"Error serving file {filename}: {str(e)}")
        return f"File not found: {filename}", 404

@app.route('/admin')
@login_required
def admin_index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template('admin/index.html', posts=posts, videos=videos)

@app.route('/admin/')
@login_required
def admin_index_slash():
    return redirect(url_for('admin_index'))

@app.route('/admin/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        author = request.form.get('author')
        
        # Debug logging
        app.logger.info(f"Form data - Title: {title}, Category: {category}, Author: {author}")
        app.logger.info(f"Content: {content}")
        
        # Check if content is empty or just contains HTML tags with no actual content
        content_without_tags = re.sub(r'<[^>]*>', '', content or '')
        content_without_tags = content_without_tags.strip()
        app.logger.info(f"Content without tags: '{content_without_tags}'")
        
        if not title:
            flash('Lütfen başlık alanını doldurun!', 'danger')
            return render_template('admin/create_post.html', categories=CATEGORIES, 
                                 form_data={'title': title, 'content': content, 'category': category, 'author': author})
        
        # Special check for CKEditor empty content patterns
        is_empty_content = (not content or 
                           content == '<p>&nbsp;</p>' or 
                           content == '<p>None</p>' or
                           content == 'None' or
                           not content_without_tags)
        
        if is_empty_content:
            app.logger.info(f"Content validation failed: '{content}'")
            flash('Lütfen içerik alanını doldurun!', 'danger')
            return render_template('admin/create_post.html', categories=CATEGORIES, 
                                 form_data={'title': title, 'content': '', 'category': category, 'author': author})
        
        app.logger.info(f"Content validation passed, creating post")
        new_post = Post(
            title=title,
            content=content,
            category=category,
            author=author
        )
        
        # Handle image upload
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            
            if file and allowed_file(file.filename):
                try:
                    # Save file
                    filename = secure_filename(file.filename)
                    timestamp = int(time.time())
                    name, ext = os.path.splitext(filename)
                    unique_filename = f"{name}_{timestamp}{ext}"
                    
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    # Resize image
                    resize_image(filepath)
                    
                    # Set image URL - use the URL path, not the file system path
                    new_post.image_url = unique_filename
                except Exception as e:
                    if 'filepath' in locals() and os.path.exists(filepath):
                        os.remove(filepath)
                    flash(f'Resim yüklenirken hata oluştu: {str(e)}', 'danger')
                    return redirect(url_for('create_post'))
            else:
                flash('Geçersiz dosya türü. Lütfen bir resim dosyası seçin.', 'danger')
                return redirect(url_for('create_post'))
        
        db.session.add(new_post)
        db.session.commit()
        flash('Hikaye başarıyla oluşturuldu!', 'success')
        return redirect(url_for('admin_index'))
    
    categories = CATEGORIES
    return render_template('admin/create_post.html', categories=categories)

@app.route('/admin/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        author = request.form.get('author')
        
        # Debug logging
        app.logger.info(f"Edit form data - Title: {title}, Category: {category}, Author: {author}, Content length: {len(content) if content else 0}")
        
        # Check if content is empty or just contains HTML tags with no actual content
        content_without_tags = re.sub(r'<[^>]*>', '', content or '')
        content_without_tags = content_without_tags.strip()
        app.logger.info(f"Content without tags: '{content_without_tags}'")
        
        if not title:
            flash('Lütfen başlık alanını doldurun!', 'danger')
            return render_template('admin/edit_post.html', post=post, categories=CATEGORIES)
        
        if not content or content == '<p>&nbsp;</p>' or not content_without_tags:
            flash('Lütfen içerik alanını doldurun!', 'danger')
            return render_template('admin/edit_post.html', post=post, categories=CATEGORIES)
        
        post.title = title
        post.content = content
        post.category = category
        post.author = author
        
        # Handle image upload
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            
            if file and allowed_file(file.filename):
                try:
                    # Delete old image if exists
                    if post.image_url:
                        if os.environ.get('FLASK_ENV') == 'production':
                            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_url)
                        else:
                            old_image_path = os.path.join(app.static_folder, post.image_url)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    # Save new file
                    filename = secure_filename(file.filename)
                    timestamp = int(time.time())
                    name, ext = os.path.splitext(filename)
                    unique_filename = f"{name}_{timestamp}{ext}"
                    
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    # Resize image
                    resize_image(filepath)
                    
                    # Set image URL
                    post.image_url = unique_filename
                except Exception as e:
                    if 'filepath' in locals() and os.path.exists(filepath):
                        os.remove(filepath)
                    flash(f'Resim yüklenirken hata oluştu: {str(e)}', 'danger')
                    return redirect(url_for('edit_post', post_id=post_id))
            else:
                flash('Geçersiz dosya türü. Lütfen bir resim dosyası seçin.', 'danger')
                return redirect(url_for('edit_post', post_id=post_id))
        
        db.session.commit()
        flash('Hikaye başarıyla güncellendi!', 'success')
        return redirect(url_for('admin_index'))
    
    categories = CATEGORIES
    return render_template('admin/edit_post.html', post=post, categories=categories)

@app.route('/admin/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Delete image if exists
    if post.image_url:
        if os.environ.get('FLASK_ENV') == 'production':
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_url)
        else:
            image_path = os.path.join(app.static_folder, post.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(post)
    db.session.commit()
    flash('Hikaye başarıyla silindi!', 'success')
    return redirect(url_for('admin_index'))

@app.route('/admin/sync-youtube', methods=['GET', 'POST'])
@login_required
def sync_youtube():
    """Admin page to sync YouTube videos"""
    # Check if API key is set
    api_key = Setting.get_value('youtube_api_key', YOUTUBE_API_KEY)
    has_api_key = bool(api_key)
    
    if request.method == 'POST':
        channel_id = request.form.get('channel_id')
        max_results = int(request.form.get('max_results', 10))
        
        if not channel_id:
            flash('Kanal ID veya kullanıcı adı gereklidir.', 'danger')
            return redirect(url_for('sync_youtube'))
        
        if not has_api_key:
            flash('YouTube API anahtarı ayarlanmamış. Lütfen önce ayarlar sayfasından API anahtarınızı ekleyin.', 'danger')
            return redirect(url_for('admin_settings'))
        
        try:
            videos_count = sync_youtube_videos(channel_id, max_results)
            flash(f'{videos_count} video başarıyla senkronize edildi.', 'success')
        except Exception as e:
            app.logger.error(f"Error syncing videos: {e}")
            flash(f'Video senkronizasyonu sırasında bir hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('videos'))
    
    return render_template('admin/sync_youtube.html', has_api_key=has_api_key)

@app.route('/admin/video/add', methods=['GET', 'POST'])
@login_required
def add_video():
    """Add a video manually"""
    form = VideoForm()
    
    if form.validate_on_submit():
        # Extract video ID if full URL is provided
        youtube_embed = form.youtube_embed.data
        
        # Check if it's a full YouTube URL and extract the video ID
        if 'youtube.com/watch?v=' in youtube_embed:
            youtube_embed = youtube_embed.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in youtube_embed:
            youtube_embed = youtube_embed.split('/')[-1].split('?')[0]
            
        # Create new video
        new_video = Video(
            title=form.title.data,
            youtube_embed=youtube_embed,
            created_at=datetime.now(UTC)
        )
        
        db.session.add(new_video)
        db.session.commit()
        
        flash('Video başarıyla eklendi.', 'success')
        return redirect(url_for('videos'))
    
    return render_template('admin/video_form.html', form=form, title='Video Ekle')

@app.route('/admin/video/edit/<int:video_id>', methods=['GET', 'POST'])
@login_required
def edit_video(video_id):
    """Edit a video"""
    video = Video.query.get_or_404(video_id)
    form = VideoForm(obj=video)
    
    if form.validate_on_submit():
        # Extract video ID if full URL is provided
        youtube_embed = form.youtube_embed.data
        
        # Check if it's a full YouTube URL and extract the video ID
        if 'youtube.com/watch?v=' in youtube_embed:
            youtube_embed = youtube_embed.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in youtube_embed:
            youtube_embed = youtube_embed.split('/')[-1].split('?')[0]
            
        video.title = form.title.data
        video.youtube_embed = youtube_embed
        
        db.session.commit()
        
        flash('Video başarıyla güncellendi.', 'success')
        return redirect(url_for('videos'))
    
    return render_template('admin/video_form.html', form=form, title='Video Düzenle')

@app.route('/admin/video/delete/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    """Delete a video"""
    video = Video.query.get_or_404(video_id)
    
    db.session.delete(video)
    db.session.commit()
    
    flash('Video başarıyla silindi.', 'success')
    return redirect(url_for('videos'))

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return db.session.get(User, int(user_id))

class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

class VideoForm(FlaskForm):
    title = StringField('Video Başlığı', validators=[DataRequired()])
    youtube_embed = StringField('YouTube Video ID', validators=[DataRequired()])
    submit = SubmitField('Kaydet')

@app.route('/')
def index():
    """Home page"""
    search_query = request.args.get('search', '')
    
    if search_query:
        # Search in title and content
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        posts_query = Post.query.filter(
            or_(
                Post.title.ilike(f'%{search_query}%'),
                Post.content.ilike(f'%{search_query}%')
            )
        ).order_by(Post.created_at.desc())
        
        posts_pagination = posts_query.paginate(page=page, per_page=per_page, error_out=False)
        posts = posts_pagination.items
        
        return render_template('category.html', 
                              posts=posts, 
                              pagination=posts_pagination,
                              category='search', 
                              category_display=f'"{search_query}" için arama sonuçları')
    else:
        # Get trending posts based on likes
        trending_posts = Post.query.order_by(Post.likes.desc()).limit(3).all()
        
        # Get recent posts
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(4).all()
        
        # Get most liked posts
        most_liked_posts = Post.query.order_by(Post.likes.desc()).limit(4).all()
        
        # Get category highlights
        category_highlights = {}
        for category, _ in CATEGORIES:
            posts = Post.query.filter_by(category=category).order_by(Post.created_at.desc()).limit(3).all()
            if posts:
                category_highlights[category] = posts
        
        # Get videos
        videos = Video.query.order_by(Video.created_at.desc()).limit(3).all()
        
        return render_template('index.html', 
                              featured_posts=trending_posts, 
                              recent_posts=recent_posts,
                              most_liked_posts=most_liked_posts,
                              category_highlights=category_highlights,
                              videos=videos)

@app.route('/category/<category>')
def category(category):
    """Category page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    posts_query = Post.query.filter_by(category=category).order_by(Post.created_at.desc())
    posts_pagination = posts_query.paginate(page=page, per_page=per_page, error_out=False)
    posts = posts_pagination.items
    
    # Get category display name
    category_display = dict(CATEGORIES).get(category, category.capitalize())
    
    return render_template('category.html', 
                          posts=posts, 
                          pagination=posts_pagination,
                          category=category, 
                          category_display=category_display)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    trending_posts = Post.get_trending_posts(5)
    approved_comments = Comment.query.filter_by(post_id=post_id, is_approved=True).order_by(Comment.created_at.desc()).all()
    
    # Debug logging
    app.logger.info(f"Post ID: {post.id}, Title: {post.title}")
    app.logger.info(f"Image URL: {post.image_url}")
    app.logger.info(f"Image URL type: {type(post.image_url)}")
    
    return render_template('post.html', post=post, trending_posts=trending_posts, comments=approved_comments)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_index'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        print(f"Login attempt for user: {username}")
        
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User found in database")
            if user.check_password(password):
                print("Password verification successful")
                login_user(user)
                flash('Başarıyla giriş yaptınız!', 'success')
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('admin_index'))
            else:
                print("Password verification failed")
                flash('Geçersiz şifre!', 'error')
        else:
            print(f"User {username} not found in database")
            flash('Kullanıcı bulunamadı!', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('index'))

@app.route('/videos')
def videos():
    """Display all videos from the database"""
    all_videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template('videos.html', videos=all_videos)

@app.route('/post/<int:post_id>/rate/<action>', methods=['POST'])
@csrf.exempt
def rate_post(post_id, action):
    """Handle post rating (like/dislike)"""
    try:
        # Log the request for debugging
        app.logger.info(f"Rating request received: post_id={post_id}, action={action}, IP={request.remote_addr}")
        
        # Validate action
        if action not in ['like', 'dislike']:
            return jsonify({'success': False, 'message': 'Geçersiz işlem'}), 400

        # Get post
        post = Post.query.get_or_404(post_id)
        
        # Check if this IP has already rated this post
        existing_rating = Rating.query.filter_by(
            post_id=post_id, 
            ip_address=request.remote_addr
        ).first()
        
        if existing_rating:
            # Only allow changing from like to dislike or vice versa
            if (existing_rating.is_like and action == 'dislike') or (not existing_rating.is_like and action == 'like'):
                # Update the existing rating
                existing_rating.is_like = (action == 'like')
                db.session.commit()
                
                # Update the post's like/dislike counts
                post.update_rating_counts()
                
                return jsonify({
                    'success': True,
                    'likes': post.likes,
                    'dislikes': post.dislikes,
                    'message': 'Oyunuz güncellendi'
                })
            else:
                # User is trying to rate again with the same action
                return jsonify({
                    'success': False,
                    'message': 'Bu yazıyı zaten oyladınız'
                })
        
        # Create a new rating
        new_rating = Rating(
            post_id=post_id,
            ip_address=request.remote_addr,
            is_like=(action == 'like')
        )
        
        db.session.add(new_rating)
        db.session.commit()
        
        # Update the post's like/dislike counts
        post.update_rating_counts()
        
        # Log the response for debugging
        app.logger.info(f"Rating successful: post_id={post_id}, new likes={post.likes}, new dislikes={post.dislikes}")
        
        return jsonify({
            'success': True,
            'likes': post.likes,
            'dislikes': post.dislikes,
            'message': 'Oyunuz kaydedildi'
        })

    except Exception as e:
        app.logger.error(f"Error rating post {post_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
        }), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle file uploads from CKEditor and other forms"""
    try:
        if 'upload' not in request.files:
            app.logger.warning("No file part in request")
            return jsonify({'error': 'No file part'})
        
        f = request.files['upload']
        if f.filename == '':
            app.logger.warning("No selected file")
            return jsonify({'error': 'No selected file'})
        
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            # Add timestamp to filename to make it unique
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(file_path)
            
            app.logger.info(f"File saved to {file_path}")
            
            # Generate URL for the file
            url = url_for('serve_upload', filename=filename)
            
            app.logger.info(f"Generated URL: {url}")
            
            # Return in the format CKEditor expects
            return jsonify({
                'url': url,
                "uploaded": 1,
                "fileName": filename
            })
        else:
            app.logger.warning(f"File type not allowed: {f.filename}")
            return jsonify({'error': 'File type not allowed'})
    except Exception as e:
        app.logger.error(f"Error uploading file: {str(e)}")
        return jsonify({'error': f'Upload error: {str(e)}'}), 500

def init_db():
    """Initialize the database with required tables and default admin user."""
    db.create_all()
    
    # Check if admin user exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(username='admin', password=generate_password_hash('admin'))
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info("Admin user created successfully")
    
    # Check if settings table exists and YouTube API key is set
    youtube_api_key = Setting.get_value('youtube_api_key')
    if youtube_api_key is None:
        # Try to get from environment variable
        env_api_key = os.environ.get('YOUTUBE_API_KEY')
        if env_api_key:
            Setting.set_value('youtube_api_key', env_api_key)
            app.logger.info("YouTube API key initialized from environment variable")
        else:
            app.logger.info("YouTube API key not found in environment variables")

    # Update old makale posts to inceleme category
    update_makale_posts()
    
    app.logger.info("Database initialized successfully")

def update_makale_posts():
    """Update posts with 'makale' category to 'inceleme'"""
    try:
        makale_posts = Post.query.filter_by(category='makale').all()
        if makale_posts:
            count = len(makale_posts)
            for post in makale_posts:
                post.category = 'inceleme'
            db.session.commit()
            app.logger.info(f"Updated {count} posts from 'makale' to 'inceleme' category")
    except Exception as e:
        app.logger.error(f"Error updating makale posts: {str(e)}")
        db.session.rollback()

@app.before_first_request
def initialize_app():
    """Initialize the app before first request"""
    try:
        init_db()
        app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Error initializing database: {str(e)}")
        raise

@app.context_processor
def inject_now():
    """Inject current datetime into templates"""
    return {'now': datetime.now(UTC)}

@app.context_processor
def inject_categories():
    """Inject categories into all templates"""
    # Create a list of category objects with name and slug properties
    categories_list = []
    for slug, name in CATEGORIES:
        categories_list.append({'slug': slug, 'name': name})
    return {'categories': categories_list}

@app.route('/author/<author>')
def author_posts(author):
    """Author posts page"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    posts_query = Post.query.filter_by(author=author).order_by(Post.created_at.desc())
    posts_pagination = posts_query.paginate(page=page, per_page=per_page, error_out=False)
    posts = posts_pagination.items
    
    return render_template('category.html', 
                          posts=posts, 
                          pagination=posts_pagination,
                          category='author', 
                          category_display=f'{author} tarafından yazılan içerikler')

@app.route('/category/makale')
def makale_redirect():
    """Redirect old makale category to new inceleme category"""
    return redirect(url_for('category', category='inceleme'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    """Admin settings page"""
    if request.method == 'POST':
        youtube_api_key = request.form.get('youtube_api_key', '').strip()
        
        # Save the API key to the database
        Setting.set_value('youtube_api_key', youtube_api_key)
        
        flash('Ayarlar başarıyla kaydedildi!', 'success')
        return redirect(url_for('admin_settings'))
    
    # Get current settings
    youtube_api_key = Setting.get_value('youtube_api_key', '')
    
    return render_template('admin/settings.html', youtube_api_key=youtube_api_key)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    
    name = request.form.get('name')
    email = request.form.get('email')
    content = request.form.get('content')
    
    if not name or not email or not content:
        flash('Lütfen tüm alanları doldurun.', 'danger')
        return redirect(url_for('post', post_id=post_id))
    
    # Simple email validation
    if '@' not in email or '.' not in email:
        flash('Geçerli bir e-posta adresi girin.', 'danger')
        return redirect(url_for('post', post_id=post_id))
    
    # Create new comment
    comment = Comment(
        post_id=post_id,
        name=name,
        email=email,
        content=content,
        ip_address=request.remote_addr
    )
    
    db.session.add(comment)
    db.session.commit()
    
    flash('Yorumunuz gönderildi ve onay bekliyor.', 'success')
    return redirect(url_for('post', post_id=post_id))

@app.route('/admin/comments')
@login_required
def admin_comments():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'pending')
    
    # Get counts for the badge indicators
    pending_count = Comment.query.filter_by(is_approved=False).count()
    approved_count = Comment.query.filter_by(is_approved=True).count()
    total_count = Comment.query.count()
    
    if status == 'approved':
        comments = Comment.query.filter_by(is_approved=True)
    elif status == 'all':
        comments = Comment.query
    else:  # pending
        comments = Comment.query.filter_by(is_approved=False)
    
    # Order by created_at descending and paginate
    paginated_comments = comments.order_by(Comment.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/comments.html', 
                          comments=paginated_comments, 
                          status=status,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          total_count=total_count,
                          pagination=paginated_comments)

@app.route('/admin/comments/approve/<int:comment_id>', methods=['POST'])
@login_required
def approve_comment(comment_id):
    try:
        comment = Comment.query.get_or_404(comment_id)
        comment.is_approved = True
        db.session.commit()
        
        flash('Yorum başarıyla onaylandı.', 'success')
        return redirect(url_for('admin_comments'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error approving comment {comment_id}: {str(e)}")
        flash(f'Yorum onaylanırken bir hata oluştu: {str(e)}', 'error')
        return redirect(url_for('admin_comments'))

@app.route('/admin/comments/delete/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """Delete a comment"""
    try:
        app.logger.info(f"Attempting to delete comment {comment_id}")
        comment = Comment.query.get_or_404(comment_id)
        
        # Store the comment details for logging
        comment_details = {
            'id': comment.id,
            'post_id': comment.post_id,
            'author': comment.name,
            'content': comment.content[:50]
        }
        
        # Delete the comment
        db.session.delete(comment)
        db.session.commit()
        
        app.logger.info(f"Successfully deleted comment: {comment_details}")
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Yorum başarıyla silindi.'
            })
        
        flash('Yorum başarıyla silindi.', 'success')
        return redirect(url_for('admin_comments'))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting comment {comment_id}: {str(e)}")
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': f'Yorum silinirken bir hata oluştu: {str(e)}'
            }), 500
        
        flash(f'Yorum silinirken bir hata oluştu: {str(e)}', 'error')
        return redirect(url_for('admin_comments'))

@app.route('/test-image')
def test_image():
    """Test route for image display"""
    return render_template('test_image.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10001))
    app.debug = True
    app.run(host='0.0.0.0', port=port)
