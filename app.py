from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_ckeditor import CKEditor, CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import ValidationError
import os
import time
from datetime import datetime
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired
from sqlalchemy import or_
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("blog.db")}'

# File upload configuration
if os.environ.get('PRODUCTION'):
    # In production, use a directory that's definitely writable
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    # In development, use the static folder
    UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure the upload directory exists
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.logger.info(f'Upload directory created at: {UPLOAD_FOLDER}')
except Exception as e:
    app.logger.error(f'Error creating upload directory: {str(e)}')
    # If we can't create the directory, use the system temp directory
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.logger.warning(f'Using fallback upload directory: {UPLOAD_FOLDER}')

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
app.logger.info(f'Upload directory: {UPLOAD_FOLDER}')
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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

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
        self.likes = Rating.query.filter_by(post_id=self.id, is_like=True).count()
        self.dislikes = Rating.query.filter_by(post_id=self.id, is_like=False).count()
        db.session.commit()

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

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        app.logger.error(f'Error serving file {filename}: {str(e)}')
        return 'File not found', 404

class PostAdmin(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    form_extra_fields = {
        'image_file': FileField('Upload Image')
    }
    
    form_widget_args = {
        'image_url': {'readonly': True}
    }
    
    column_list = ('title', 'category', 'created_at', 'likes', 'dislikes')
    form_columns = ('title', 'content', 'category', 'image_file')
    
    def handle_file_upload(self, file):
        """Handle file upload with proper error handling"""
        if not file:
            return None
            
        if not allowed_file(file.filename):
            app.logger.warning(f'Invalid file type: {file.filename}')
            raise ValueError('Invalid file type. Allowed types are: png, jpg, jpeg, gif')
            
        try:
            # Generate a unique filename
            original_filename = secure_filename(file.filename)
            name, ext = os.path.splitext(original_filename)
            timestamp = int(time.time())
            unique_filename = f"{name}_{timestamp}{ext}"
            
            # Ensure the upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Verify the file was saved
            if not os.path.exists(file_path):
                raise ValueError('Failed to save file')
                
            app.logger.info(f'Successfully saved image: {unique_filename}')
            
            # Return the URL path
            if os.environ.get('PRODUCTION'):
                return f'/uploads/{unique_filename}'  # Use the uploads route in production
            else:
                return f'/static/uploads/{unique_filename}'  # Use static route in development
            
        except Exception as e:
            app.logger.error(f'Error saving image: {str(e)}')
            raise ValueError(f'Failed to save image: {str(e)}')
    
    def on_model_change(self, form, model, is_created):
        """Handle model changes with proper error handling"""
        try:
            file = form.image_file.data
            if file:
                image_url = self.handle_file_upload(file)
                if image_url:
                    model.image_url = image_url
        except ValueError as e:
            flash(str(e), 'error')
            raise ValidationError(str(e))
        except Exception as e:
            app.logger.error(f'Unexpected error in on_model_change: {str(e)}')
            flash('An unexpected error occurred while saving the image', 'error')
            raise

    form_overrides = {
        'content': CKEditorField
    }
    form_choices = {'category': CATEGORIES}

class VideoAdmin(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    column_list = ('title', 'youtube_embed', 'created_at')
    form_columns = ('title', 'youtube_embed')

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş Yap')

admin = Admin(app, name='HepsiHikaye Admin', template_mode='bootstrap3', index_view=MyAdminIndexView())
admin.add_view(PostAdmin(Post, db.session))
admin.add_view(VideoAdmin(Video, db.session))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 6
    
    # Get regular posts with pagination
    pagination = Post.query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    posts = pagination.items
    
    # Get trending and most liked posts
    trending_posts = Post.get_trending_posts(limit=3)
    most_liked_posts = Post.get_most_liked_posts(limit=3)
    
    return render_template('index.html',
                         posts=posts,
                         trending_posts=trending_posts,
                         most_liked_posts=most_liked_posts,
                         pagination=pagination)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        print(f"Login attempt for user: {username}")
        
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User found in database")
            if check_password_hash(user.password, password):
                print("Password verification successful")
                login_user(user)
                flash('Başarıyla giriş yaptınız!', 'success')
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('admin.index'))
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

@app.route('/admin')
@login_required
def admin_index():
    return redirect('/admin/')

@app.route('/category/<category>')
def category(category):
    if category == 'video':
        videos = Video.query.order_by(Video.created_at.desc()).all()
        return render_template('videos.html', 
                             videos=videos,
                             current_year=datetime.now().year,
                             active_category=category)
    
    posts = Post.query.filter_by(category=category).order_by(Post.created_at.desc()).all()
    return render_template('category.html', 
                         posts=posts,
                         category_name=category.capitalize(),
                         current_year=datetime.now().year,
                         active_category=category)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

@app.route('/post/<int:post_id>/rate/<action>')
def rate_post(post_id, action):
    if action not in ['like', 'dislike']:
        return jsonify({'error': 'Invalid action'}), 400
        
    post = Post.query.get_or_404(post_id)
    ip_address = request.remote_addr
    
    # Check if user already rated
    existing_rating = Rating.query.filter_by(
        post_id=post_id,
        ip_address=ip_address
    ).first()
    
    if existing_rating:
        if (existing_rating.is_like and action == 'like') or \
           (not existing_rating.is_like and action == 'dislike'):
            # Remove rating if clicking the same button again
            db.session.delete(existing_rating)
        else:
            # Change rating if clicking the opposite button
            existing_rating.is_like = (action == 'like')
    else:
        # Create new rating
        new_rating = Rating(
            post_id=post_id,
            ip_address=ip_address,
            is_like=(action == 'like')
        )
        db.session.add(new_rating)
    
    db.session.commit()
    post.update_rating_counts()
    
    return jsonify({
        'likes': post.likes,
        'dislikes': post.dislikes
    })

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
        url = url_for('static', filename=f'uploads/{filename}')
        
        # Return in the format CKEditor expects
        return jsonify({
            'url': url,
            "uploaded": 1,
            "fileName": filename
        })
    
    return jsonify({'error': 'File type not allowed'})

def init_db():
    with app.app_context():
        print("Dropping all tables...")  # Debug log
        db.drop_all()
        print("Creating all tables...")  # Debug log
        db.create_all()
        print("Tables created successfully")  # Debug log
        
        # Create admin user
        admin_username = 'elnidal'
        admin_password = 'm37479673m'
        
        print(f"Creating admin user: {admin_username}")
        admin = User(
            username=admin_username,
            password=generate_password_hash(admin_password, method='sha256')
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully")

@app.before_first_request
def initialize_app():
    print("Initializing application...")
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
