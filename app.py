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
        return url_for('static', filename=f'uploads/{post.image}')
    return url_for('static', filename='uploads/default_post_image.png')

# Routes
@app.route('/')
def index():
    try:
        # Get recent posts and videos
        recent_posts = Post.query.filter_by(published=True).order_by(Post.created_at.desc()).limit(9).all()
        recent_videos = Video.query.filter_by(published=True).order_by(Video.created_at.desc()).limit(3).all()
        
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
                featured=featured
            )
            
            # Handle image upload
            if image and image.filename:
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                image_path = os.path.join('static', 'uploads', filename)
                
                # Ensure uploads directory exists
                os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                
                # Save the image
                image.save(image_path)
                
                # Resize image if needed
                resize_image(image_path)
                
                new_post.image = filename
            
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
            
            # Handle image
            if remove_image and post.image:
                # Remove the image file (optional)
                try:
                    image_path = os.path.join('static', 'uploads', post.image)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    app.logger.error(f"Error removing image: {str(e)}")
                
                # Remove image reference
                post.image = None
            
            if image and image.filename:
                # Save new image
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image.filename}")
                image_path = os.path.join('static', 'uploads', filename)
                
                # Ensure uploads directory exists
                os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
                
                # Save the image
                image.save(image_path)
                
                # Resize image if needed
                resize_image(image_path)
                
                post.image = filename
            
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

@app.route('/admin/comments')
@login_required
def admin_comments():
    try:
        comments = Comment.query.all()
        return render_template('admin/comments.html', comments=comments)
    except Exception as e:
        app.logger.error(f"Admin comments error: {str(e)}")
        return redirect(url_for('admin_dashboard'))

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
        return render_template('admin/settings.html')
    except Exception as e:
        app.logger.error(f"Admin settings error: {str(e)}")
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

@app.route('/admin/videos')
@login_required
def admin_videos():
    try:
        videos = Video.query.all()
        return render_template('admin/videos.html', videos=videos)
    except Exception as e:
        app.logger.error(f"Admin videos error: {str(e)}")
        flash('Videoları yüklerken bir hata oluştu!', 'danger')
        return render_template('admin/videos.html', videos=[])

@app.route('/admin/new-video', methods=['GET', 'POST'])
@login_required
def admin_new_video():
    try:
        categories = Category.query.all()
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            url = request.form.get('url')
            thumbnail_url = request.form.get('thumbnail_url')
            category_id = int(request.form.get('category_id')) if request.form.get('category_id') else None
            
            # Create new video
            new_video = Video(
                title=title,
                description=description,
                url=url,
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
        flash('Video eklenirken bir hata oluştu!', 'danger')
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
                'fileName': filename
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
        # Check if any users exist
        if User.query.count() == 0:
            # Create default admin user
            admin = User(
                username='admin',
                password=generate_password_hash('admin')
            )
            db.session.add(admin)
            
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
        
        # Load posts and videos from JSON files
        posts = load_data(POSTS_FILE, [])
        videos = load_data(VIDEOS_FILE, [])
        
        # Filter posts and videos by query
        matching_posts = [p for p in posts if 
                         query.lower() in p.get('title', '').lower() or 
                         query.lower() in p.get('content', '').lower()]
        
        matching_videos = [v for v in videos if 
                          query.lower() in v.get('title', '').lower() or 
                          query.lower() in v.get('description', '').lower()]
        
        # Format dates for videos (Posts handled by filter)
        for video in matching_videos:
            if isinstance(video.get('created_at'), str):
                video['formatted_date'] = format_datetime_filter(video['created_at'])
        
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
        
    # Run the app
    app.run(debug=True, port=8080)
else:
    # This code runs when imported (e.g., by Gunicorn in production)
    # Ensure required directories exist
    for directory in ['uploads', 'logs']:
        path = os.path.join(app.static_folder, directory)
        if not os.path.exists(path):
            os.makedirs(path)
            app.logger.info(f"Created directory: {path}")
    
    # Initialize database when the app starts
    with app.app_context():
        db.create_all()
        initialize_database()
        
        # Optional: Migrate from JSON files
        if os.path.exists(DATA_DIR):
            try:
                migrate_from_json()
            except Exception as e:
                app.logger.error(f"Failed to migrate from JSON: {str(e)}") 