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
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Custom exception for validation errors
class ValidationError(Exception):
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("blog.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder based on environment
if os.environ.get('FLASK_ENV') == 'production':
    # In production (Render.com), use a directory that persists between deployments
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    # URL path for uploads in production
    app.config['UPLOAD_URL'] = 'uploads'
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
    app.config['UPLOAD_URL'] = 'uploads'  # URL path for uploads

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# CKEditor configuration
app.config['CKEDITOR_ENABLE_CSRF'] = True
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'
app.config['CKEDITOR_HEIGHT'] = 400
app.config['CKEDITOR_CONFIG'] = {
    'toolbar': [
        ['Style', 'Format', 'Font', 'FontSize'],
        ['Bold', 'Italic', 'Underline', 'Strike'],
        ['TextColor', 'BGColor'],
        ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote'],
        ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
        ['Link', 'Unlink'],
        ['Image', 'Table'],
        ['Undo', 'Redo'],
        ['RemoveFormat', 'Source']
    ],
    'filebrowserUploadUrl': '/upload',
    'removeDialogTabs': 'image:advanced;link:advanced',
    'language': 'tr',
    'extraPlugins': 'image2,uploadimage',
    'removePlugins': 'image',
    'disableNativeSpellChecker': False,
    'disableReadonlyStyling': True,
    'ignoreEmptyParagraph': True,
    'allowedContent': True,
    'extraAllowedContent': '*(*);*{*}',
    'startupShowBorders': False
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
    ('makale', 'Makale'),
    ('haber', 'Haber'),
    ('video', 'Video'),
]

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # Store IP to prevent multiple votes
    is_like = db.Column(db.Boolean, nullable=False)  # True for like, False for dislike
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    ratings = db.relationship('Rating', backref='post', lazy=True)

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
        time_diff = datetime.utcnow() - self.created_at
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # Only resize if image is larger than max_size
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(image_path, 'JPEG', quality=85)
                app.logger.info(f'Resized image: {image_path}')
    except Exception as e:
        app.logger.error(f'Error resizing image {image_path}: {str(e)}')

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, serve from the /tmp/uploads directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        # In development, serve from the static/uploads directory
        return redirect(url_for('static', filename=f'uploads/{filename}'))

@app.route('/admin')
@login_required
def admin_index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/index.html', posts=posts, now=datetime.now())

@app.route('/admin/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        
        # Debug logging
        app.logger.info(f"Form data - Title: {title}, Category: {category}")
        app.logger.info(f"Content: {content}")
        
        # Check if content is empty or just contains HTML tags with no actual content
        content_without_tags = re.sub(r'<[^>]*>', '', content or '')
        content_without_tags = content_without_tags.strip()
        app.logger.info(f"Content without tags: '{content_without_tags}'")
        
        if not title:
            flash('Lütfen başlık alanını doldurun!', 'danger')
            return render_template('admin/create_post.html', categories=CATEGORIES, 
                                 now=datetime.now(), form_data={'title': title, 'content': content, 'category': category})
        
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
                                 now=datetime.now(), form_data={'title': title, 'content': '', 'category': category})
        
        app.logger.info(f"Content validation passed, creating post")
        new_post = Post(
            title=title,
            content=content,
            category=category
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
    return render_template('admin/create_post.html', categories=categories, now=datetime.now())

@app.route('/admin/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        
        # Debug logging
        app.logger.info(f"Edit form data - Title: {title}, Category: {category}, Content length: {len(content) if content else 0}")
        
        # Check if content is empty or just contains HTML tags with no actual content
        content_without_tags = re.sub(r'<[^>]*>', '', content or '')
        content_without_tags = content_without_tags.strip()
        app.logger.info(f"Content without tags: '{content_without_tags}'")
        
        if not title:
            flash('Lütfen başlık alanını doldurun!', 'danger')
            return render_template('admin/edit_post.html', post=post, categories=CATEGORIES, now=datetime.now())
        
        if not content or content == '<p>&nbsp;</p>' or not content_without_tags:
            flash('Lütfen içerik alanını doldurun!', 'danger')
            return render_template('admin/edit_post.html', post=post, categories=CATEGORIES, now=datetime.now())
        
        post.title = title
        post.content = content
        post.category = category
        
        # Handle image upload
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            
            if file and allowed_file(file.filename):
                try:
                    # Delete old image if exists
                    if post.image_url:
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
    return render_template('admin/edit_post.html', post=post, categories=categories, now=datetime.now())

@app.route('/admin/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Delete image if exists
    if post.image_url:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(post.image_url))
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(post)
    db.session.commit()
    flash('Hikaye başarıyla silindi!', 'success')
    return redirect(url_for('admin_index'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

@app.route('/')
def index():
    """Home page"""
    search_query = request.args.get('search', '')
    
    if search_query:
        # Search in title and content
        posts = Post.query.filter(
            or_(
                Post.title.ilike(f'%{search_query}%'),
                Post.content.ilike(f'%{search_query}%')
            )
        ).order_by(Post.created_at.desc()).all()
        return render_template('category.html', posts=posts, 
                              category='search', 
                              category_display=f'"{search_query}" için arama sonuçları', 
                              now=datetime.now())
    else:
        # Get featured posts (most liked)
        featured_posts = Post.query.order_by(Post.likes.desc()).limit(3).all()
        
        # Get recent posts
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(4).all()
        
        # Get category highlights
        category_highlights = {}
        for category_id, _ in CATEGORIES:
            posts = Post.query.filter_by(category=category_id).order_by(Post.created_at.desc()).limit(3).all()
            if posts:
                category_highlights[category_id] = posts
        
        return render_template('index.html', 
                              featured_posts=featured_posts,
                              recent_posts=recent_posts,
                              category_highlights=category_highlights,
                              CATEGORIES=CATEGORIES,
                              now=datetime.now())

@app.route('/category/<category>')
def category(category):
    """Category page"""
    posts = Post.query.filter_by(category=category).order_by(Post.created_at.desc()).all()
    
    # Get category display name
    category_display = dict(CATEGORIES).get(category, category.capitalize())
    
    return render_template('category.html', posts=posts, category=category, 
                          category_display=category_display, now=datetime.now())

@app.route('/post/<int:post_id>')
def post(post_id):
    """Post detail page"""
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post, now=datetime.now())

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
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/rate/<action>', methods=['POST'])
def rate_post(post_id, action):
    """Handle post rating (like/dislike)"""
    try:
        if action not in ['like', 'dislike']:
            return jsonify({'success': False, 'message': 'Geçersiz işlem'}), 400

        post = Post.query.get_or_404(post_id)
        rating = Rating.query.filter_by(
            post_id=post_id,
            ip_address=request.remote_addr
        ).first()

        if rating:
            # Update existing rating
            if (action == 'like' and not rating.is_like) or (action == 'dislike' and rating.is_like):
                rating.is_like = (action == 'like')
                db.session.commit()
        else:
            # Create new rating
            new_rating = Rating(
                post_id=post_id,
                ip_address=request.remote_addr,
                is_like=(action == 'like')
            )
            db.session.add(new_rating)
            db.session.commit()

        # Update post rating counts
        post.update_rating_counts()
        
        return jsonify({
            'success': True,
            'likes': post.likes,
            'dislikes': post.dislikes
        })

    except Exception as e:
        app.logger.error(f"Error rating post {post_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
        }), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'upload' not in request.files:
        return jsonify({'error': 'No file part'})
    
    f = request.files['upload']
    if f.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if f and allowed_file(f.filename):
        filename = secure_filename(f.filename)
        # Add timestamp to filename to make it unique
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"
        
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        url = os.path.join(app.config['UPLOAD_URL'], filename)
        
        # Return in the format CKEditor expects
        return jsonify({
            'url': url,
            "uploaded": 1,
            "fileName": filename
        })
    
    return jsonify({'error': 'File type not allowed'})

def init_db():
    """Initialize the database with required data"""
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')  # Default password for development
        admin_user = User(
            username='admin',
            password=generate_password_hash(admin_password)
        )
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info("Admin user created successfully")

@app.before_first_request
def initialize_app():
    """Initialize the app before first request"""
    try:
        init_db()
        app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Error initializing database: {str(e)}")
        raise

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10001))
    app.debug = True
    app.run(host='0.0.0.0', port=port)
