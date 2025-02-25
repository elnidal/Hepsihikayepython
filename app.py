from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm, CSRFProtect
from flask_ckeditor import CKEditor, CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired
from sqlalchemy import or_, func
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
import os
import time

# Custom exception for validation errors
class ValidationError(Exception):
    pass

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("blog.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder based on environment
if os.environ.get('PRODUCTION'):
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    app.config['UPLOAD_URL'] = '/uploads'  # URL path for uploads
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
    'language': 'tr'
}

# Configure logging
if os.environ.get('PRODUCTION'):
    # In production, log to a file
    if not os.path.exists('logs'):
        os.makedirs('logs')
    file_handler = RotatingFileHandler('logs/hepsihikaye.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('HepsiHikaye startup')

# Log important configuration
app.logger.info(f'Upload directory: {app.config["UPLOAD_FOLDER"]}')
app.logger.info(f'Environment: {"Production" if os.environ.get("PRODUCTION") else "Development"}')
app.logger.info(f'Static folder: {app.static_folder}')

@app.after_request
def after_request(response):
    if not os.environ.get('PRODUCTION'):
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
    ('şiir', 'Şiir'),
    ('öykü', 'Öykü'),
    ('roman', 'Roman'),
    ('deneme', 'Deneme'),
    ('makale', 'Makale'),
    ('haber', 'Haber')
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
    """Serve uploaded files in production"""
    if os.environ.get('PRODUCTION'):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    return redirect(url_for('static', filename=f'uploads/{filename}'))

class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        flash('Lütfen giriş yapın!', 'warning')
        return redirect(url_for('login', next=request.url))

class PostAdmin(SecureModelView):
    column_list = ('title', 'category', 'created_at')
    form_columns = ('title', 'content', 'category', 'image')
    form_extra_fields = {
        'image': FileField('Resim')
    }
    form_overrides = {
        'content': CKEditorField
    }
    form_choices = {'category': CATEGORIES}

    def on_model_change(self, form, model, is_created):
        """Handle image upload"""
        try:
            file = form.image.data
            if file:
                filename = secure_filename(file.filename)
                timestamp = int(time.time())
                name, ext = os.path.splitext(filename)
                unique_filename = f"{name}_{timestamp}{ext}"
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                
                # Validate and resize image
                with open(filepath, 'rb') as img_file:
                    validate_image(img_file)
                resize_image(filepath)
                
                model.image_url = os.path.join('uploads', unique_filename)
        except Exception as e:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            raise ValidationError(str(e))

    def delete_model(self, model):
        """Delete image when post is deleted"""
        try:
            if model.image_url:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(model.image_url))
                if os.path.exists(image_path):
                    os.remove(image_path)
            return super().delete_model(model)
        except Exception as e:
            app.logger.error(f"Error deleting post: {str(e)}")
            raise

class VideoAdmin(SecureModelView):
    column_list = ('title', 'youtube_embed', 'created_at')
    form_columns = ('title', 'youtube_embed')

# Initialize admin interface
admin = Admin(app, name='HepsiHikaye Admin', template_mode='bootstrap3')
admin.add_view(PostAdmin(Post, db.session, name='Hikayeler'))
admin.add_view(VideoAdmin(Video, db.session, name='Videolar'))

@app.route('/admin')
@login_required
def admin_index():
    """Admin dashboard page"""
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/index.html', posts=posts)

@app.route('/post/create', methods=['GET', 'POST'])
@login_required
def create_post():
    """Create a new post"""
    if request.method == 'POST':
        try:
            title = request.form['title']
            content = request.form['content']
            category = request.form['category']
            image = request.files.get('image')
            
            post = Post(title=title, content=content, category=category)
            
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                timestamp = int(time.time())
                name, ext = os.path.splitext(filename)
                unique_filename = f"{name}_{timestamp}{ext}"
                
                # Ensure upload directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(filepath)
                
                # Validate and resize image
                with open(filepath, 'rb') as img_file:
                    validate_image(img_file)
                resize_image(filepath)
                
                post.image_url = os.path.join('uploads', unique_filename)
            
            db.session.add(post)
            db.session.commit()
            flash('Hikaye başarıyla oluşturuldu!', 'success')
            return redirect(url_for('admin_index'))
            
        except Exception as e:
            db.session.rollback()
            flash(str(e), 'error')
            
    return render_template('admin/create_post.html', categories=CATEGORIES)

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Edit an existing post"""
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        try:
            post.title = request.form['title']
            post.content = request.form['content']
            post.category = request.form['category']
            
            image = request.files.get('image')
            if image and allowed_file(image.filename):
                # Delete old image if it exists
                if post.image_url:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(post.image_url))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                filename = secure_filename(image.filename)
                timestamp = int(time.time())
                name, ext = os.path.splitext(filename)
                unique_filename = f"{name}_{timestamp}{ext}"
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(filepath)
                
                # Validate and resize image
                with open(filepath, 'rb') as img_file:
                    validate_image(img_file)
                resize_image(filepath)
                
                post.image_url = os.path.join('uploads', unique_filename)
            
            db.session.commit()
            flash('Hikaye başarıyla güncellendi!', 'success')
            return redirect(url_for('admin_index'))
            
        except Exception as e:
            db.session.rollback()
            flash(str(e), 'error')
    
    return render_template('admin/edit_post.html', post=post, categories=CATEGORIES)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    """Delete a post"""
    post = Post.query.get_or_404(post_id)
    try:
        # Delete the post's image if it exists
        if post.image_url:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(post.image_url))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(post)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting post: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Get posts with pagination
        posts = Post.query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
            
        if posts is None:
            app.logger.error("No posts found or database error")
            return render_template('index.html', 
                                posts=[], 
                                trending_posts=[], 
                                most_liked_posts=[])
            
        # Get trending and most liked posts for sidebars
        try:
            trending_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        except Exception as e:
            app.logger.error(f"Error getting trending posts: {str(e)}")
            trending_posts = []
            
        try:
            most_liked_posts = Post.query.order_by(Post.likes.desc()).limit(5).all()
        except Exception as e:
            app.logger.error(f"Error getting most liked posts: {str(e)}")
            most_liked_posts = []
        
        return render_template('index.html',
                             posts=posts,
                             trending_posts=trending_posts,
                             most_liked_posts=most_liked_posts)
                             
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', 
                             posts=[], 
                             trending_posts=[], 
                             most_liked_posts=[])

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

@app.route('/category/<category_name>')
def category(category_name):
    """Display posts for a specific category"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        posts = Post.query.filter_by(category=category_name)\
            .order_by(Post.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
            
        if posts is None:
            app.logger.error(f"No posts found for category: {category_name}")
            return render_template('category.html', 
                                posts=[], 
                                category_name=category_name)
        
        return render_template('category.html',
                             posts=posts,
                             category_name=category_name)
                             
    except Exception as e:
        app.logger.error(f"Error in category route: {str(e)}")
        flash('Bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'error')
        return redirect(url_for('index'))

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    """Display a single post with its full content"""
    try:
        post = Post.query.get_or_404(post_id)
        # Get related posts from the same category
        related_posts = Post.query.filter(
            Post.category == post.category,
            Post.id != post.id
        ).order_by(Post.created_at.desc()).limit(3).all()
        
        return render_template('post_detail.html', 
                             post=post,
                             related_posts=related_posts)
    except Exception as e:
        app.logger.error(f"Error displaying post {post_id}: {str(e)}")
        flash('Bu yazıya şu anda ulaşılamıyor.', 'error')
        return redirect(url_for('index'))

@app.route('/post/<int:post_id>/detail')
def post_detail_route(post_id):
    return redirect(url_for('post_detail', post_id=post_id))

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
    port = int(os.environ.get('PORT', 10000))
    app.debug = True
    app.run(host='0.0.0.0', port=port)
