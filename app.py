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
from markupsafe import Markup
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///hepsihikaye.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADS_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['DEBUG'] = True  # Enable debugging
app.config['TESTING'] = False
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

@app.before_request
def log_request_info():
    app.logger.info('Request: %s %s', request.method, request.path)
    if request.form:
        app.logger.debug('Form Data: %s', request.form.to_dict())
    if request.args:
        app.logger.debug('Request Args: %s', request.args.to_dict())

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f'Page not found: {request.url}')
    return "Page not found. Please check the URL.", 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'Server Error: {error}')
    return "Internal server error. Please contact the administrator.", 500

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
ckeditor = CKEditor(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Lütfen giriş yapın!'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    posts = db.relationship('Post', backref='category', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(200), nullable=True)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    published = db.Column(db.Boolean, default=True)
    featured = db.Column(db.Boolean, default=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', lazy=True)
    
    def get_category_display(self):
        return self.category.name if self.category else "Kategorisiz"
    
    def get_image_url(self):
        try:
            if hasattr(self, 'image') and self.image:
                return url_for('static', filename=f'uploads/{self.image}')
            return url_for('static', filename='images/default-post.jpg')
        except Exception as e:
            app.logger.error(f"Error getting image URL: {str(e)}")
            return url_for('static', filename='images/default-post.jpg')

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    youtube_id = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    comments = db.relationship('Comment', backref='video', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))

def init_db():
    try:
        with app.app_context():
            # In production, don't drop tables
            is_production = os.environ.get('FLASK_ENV') == 'production'
            
            if not is_production:
                # Drop all tables in development only
                db.drop_all()
                app.logger.info("Dropped all existing tables")

            # Create all tables if they don't exist
            db.create_all()
            app.logger.info("Database tables created successfully")

            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                # Create default admin user
                admin = User(
                    username='admin',
                    password=generate_password_hash('admin')
                )
                db.session.add(admin)
                db.session.commit()
                app.logger.info("Default admin user created")
            else:
                app.logger.info("Admin user already exists")

            # Create default categories if they don't exist
            default_categories = [
                {'name': 'Öykü', 'slug': 'oyku'},
                {'name': 'Roman', 'slug': 'roman'},
                {'name': 'Şiir', 'slug': 'siir'},
                {'name': 'Deneme', 'slug': 'deneme'},
                {'name': 'İnceleme', 'slug': 'inceleme'},
                {'name': 'Haber', 'slug': 'haber'},
                {'name': 'Video', 'slug': 'video'}
            ]

            for cat_data in default_categories:
                category = Category.query.filter_by(slug=cat_data['slug']).first()
                if not category:
                    category = Category(name=cat_data['name'], slug=cat_data['slug'])
                    db.session.add(category)
            
            db.session.commit()
            app.logger.info("Default categories created")

            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join(app.static_folder, 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
                app.logger.info("Uploads directory created")

    except Exception as e:
        app.logger.error(f"Database initialization error: {str(e)}")
        raise

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('admin_dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember', False)
            
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user, remember=remember)
                app.logger.info(f"User {username} logged in successfully")
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Geçersiz kullanıcı adı veya şifre.', 'error')
                app.logger.warning(f"Failed login attempt for user {username}")
        
        return render_template('admin/login.html')
    except Exception as e:
        app.logger.error(f"Login error: {str(e)}")
        flash('Giriş yapılırken bir hata oluştu.', 'error')
        return render_template('admin/login.html')

@app.route('/admin')
@login_required
def admin_index():
    try:
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        app.logger.error(f"Admin index error: {str(e)}")
        flash('Admin paneline erişimde bir hata oluştu.', 'error')
        return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    try:
        total_posts = Post.query.count()
        total_videos = Video.query.count()
        total_comments = Comment.query.count()
        total_views = db.session.query(db.func.sum(Post.views)).scalar() or 0
        
        # Get most recent posts
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
        
        # Get most recent videos
        recent_videos = Video.query.order_by(Video.created_at.desc()).limit(5).all()
        
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
        flash('Dashboard yüklenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
        return redirect(url_for('admin_login'))

@app.route('/admin/logout')
@login_required
def admin_logout():
    try:
        logout_user()
        flash('Başarıyla çıkış yaptınız.', 'success')
        return redirect(url_for('admin_login'))
    except Exception as e:
        app.logger.error(f"Logout error: {str(e)}")
        flash('Çıkış yapılırken bir hata oluştu.', 'error')
        return redirect(url_for('admin_login'))

@app.route('/')
def index():
    try:
        # Get featured content for homepage
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(6).all()
        recent_videos = Video.query.order_by(Video.created_at.desc()).limit(3).all()
        return render_template('index.html', posts=recent_posts, videos=recent_videos)
    except Exception as e:
        app.logger.error(f"Index error: {str(e)}")
        try:
            # Rollback any failed transaction
            db.session.rollback()
            
            # Fallback query without depending on new fields that might not exist yet
            app.logger.info("Falling back to simpler query")
            try:
                # Use a new connection to avoid transaction issues
                with db.engine.connect() as conn:
                    # Execute a simple raw SQL query to get basic post data
                    recent_posts = conn.execute(
                        text("SELECT id, title, content, created_at FROM post ORDER BY created_at DESC LIMIT 6")
                    ).fetchall()
                    
                    # Get videos with a separate query
                    recent_videos = Video.query.order_by(Video.created_at.desc()).limit(3).all()
                    
                    return render_template('index.html', posts=recent_posts, videos=recent_videos)
            except Exception as db_error:
                app.logger.error(f"Database connection error: {str(db_error)}")
                # If we still can't connect, return a minimal page without database content
                return render_template('errors/500.html')
        except Exception as inner_e:
            app.logger.error(f"Fallback index error: {str(inner_e)}")
            # Use a simpler error template without complex URL generation
            return "Server Error. Please contact the administrator.", 500

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        post.views += 1
        db.session.commit()
        
        # Get comments for this post
        comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
        
        # Format dates for display
        for comment in comments:
            comment.formatted_date = comment.created_at.strftime('%d.%m.%Y %H:%M')
        
        return render_template('post.html', post=post, comments=comments)
    except Exception as e:
        app.logger.error(f"Post detail error: {str(e)}")
        return "An error occurred loading this post.", 500

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        content = request.form.get('content')
        
        # Validate required fields
        if not name or not content:
            flash('İsim ve yorum alanları zorunludur.', 'danger')
            return redirect(url_for('post_detail', post_id=post_id))
        
        # Create new comment
        comment = Comment(
            author_name=name,
            content=content,
            post_id=post_id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        flash('Yorumunuz başarıyla eklendi.', 'success')
        return redirect(url_for('post_detail', post_id=post_id))
    except Exception as e:
        app.logger.error(f"Add comment error: {str(e)}")
        flash('Yorumunuz eklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))

@app.route('/post/<int:post_id>/rate/<action>', methods=['POST'])
def rate_post(post_id, action):
    try:
        post = Post.query.get_or_404(post_id)
        
        # Check if action is valid
        if action not in ['like', 'dislike']:
            return jsonify({
                'success': False,
                'message': 'Geçersiz işlem.'
            })
        
        # For simplicity, we'll just increment the count without checking for duplicate votes
        # In a real application, you'd track user IPs or require login to prevent multiple votes
        
        if action == 'like':
            # Add likes field to Post model if it doesn't exist
            if not hasattr(post, 'likes'):
                post.likes = 0
            post.likes = post.likes + 1 if post.likes else 1
        else:
            # Add dislikes field to Post model if it doesn't exist
            if not hasattr(post, 'dislikes'):
                post.dislikes = 0
            post.dislikes = post.dislikes + 1 if post.dislikes else 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'likes': post.likes or 0,
            'dislikes': post.dislikes or 0,
            'message': 'Oyunuz kaydedildi!'
        })
    except Exception as e:
        app.logger.error(f"Rate post error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
        })

@app.route('/video/<int:video_id>')
def video_detail(video_id):
    try:
        video = Video.query.get_or_404(video_id)
        return render_template('video_detail.html', video=video)
    except Exception as e:
        app.logger.error(f"Video detail error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/videos')
def videos():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 12
        videos = Video.query.order_by(Video.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        return render_template('videos.html', videos=videos)
    except Exception as e:
        app.logger.error(f"Videos page error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/admin/posts')
@login_required
def admin_posts():
    try:
        search_query = request.args.get('search', '')
        if search_query:
            posts = Post.query.options(joinedload(Post.category)).filter(
                or_(
                    Post.title.ilike(f'%{search_query}%'),
                    Post.content.ilike(f'%{search_query}%')
                )
            ).order_by(Post.created_at.desc()).all()
        else:
            posts = Post.query.options(joinedload(Post.category)).order_by(Post.created_at.desc()).all()
        return render_template('admin/posts.html', posts=posts, search_query=search_query)
    except Exception as e:
        app.logger.error(f"Admin posts error: {str(e)}")
        flash('Gönderiler yüklenirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    try:
        categories = Category.query.all()
        
        # Process form submission
        if request.method == 'POST':
            app.logger.info("Received POST request to create new post")
            # Log form data
            form_data = {k: v for k, v in request.form.items() if k != 'content'}
            app.logger.info(f"Form data (excluding content): {form_data}")
            app.logger.info(f"Content received: {'Yes' if request.form.get('content') else 'No'}")
            app.logger.info(f"Files: {request.files}")
            
            # Get form fields
            title = request.form.get('title')
            content = request.form.get('content')
            category_id = request.form.get('category_id')
            excerpt = request.form.get('excerpt')
            published = request.form.get('published') == 'on'
            featured = request.form.get('featured') == 'on'
            image = request.files.get('image')
            
            # Validate required fields
            if not title:
                app.logger.warning("Title is missing")
                flash('Başlık alanı zorunludur.', 'error')
                return render_template('admin/post_form.html', categories=categories)
            
            if not content:
                app.logger.warning("Content is missing")
                flash('İçerik alanı zorunludur.', 'error')
                return render_template('admin/post_form.html', categories=categories)
            
            # Create post object
            app.logger.info("Creating new post object")
            post = Post(
                title=title, 
                content=content,
                category_id=category_id if category_id else None,
                excerpt=excerpt,
                published=published,
                featured=featured
            )
            
            # Handle image upload
            if image and image.filename:
                app.logger.info(f"Processing image: {image.filename}")
                
                # Ensure uploads directory exists
                uploads_dir = os.path.join(app.static_folder, 'uploads')
                if not os.path.exists(uploads_dir):
                    app.logger.info(f"Creating uploads directory: {uploads_dir}")
                    os.makedirs(uploads_dir)
                
                # Save image
                filename = secure_filename(image.filename)
                image_path = os.path.join(uploads_dir, filename)
                app.logger.info(f"Saving image to: {image_path}")
                image.save(image_path)
                post.image = filename
            
            # Save post to database
            try:
                app.logger.info("Adding post to database")
                db.session.add(post)
                db.session.commit()
                app.logger.info(f"Post created successfully with ID: {post.id}")
                flash('Gönderi başarıyla oluşturuldu.', 'success')
                return redirect(url_for('admin_posts'))
            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f"Database error: {str(e)}")
                flash('Veritabanı hatası: Gönderi kaydedilemedi.', 'error')
                return render_template('admin/post_form.html', categories=categories)
        
        # Display form
        return render_template('admin/post_form.html', categories=categories, ckeditor=ckeditor)
    except Exception as e:
        app.logger.error(f"New post error: {str(e)}")
        app.logger.exception("Exception details:")
        flash('Gönderi oluşturulurken bir hata oluştu.', 'error')
        return redirect(url_for('admin_posts'))

@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    try:
        app.logger.info(f"Fetching post with ID: {post_id}")
        post = Post.query.get_or_404(post_id)
        categories = Category.query.all()
        
        if request.method == 'POST':
            app.logger.info(f"Received POST request to edit post {post_id}")
            app.logger.info(f"Form data: {request.form.to_dict()}")
            app.logger.info(f"Files: {request.files}")
            
            post.title = request.form.get('title')
            post.content = request.form.get('content')
            post.category_id = request.form.get('category_id') or None
            post.excerpt = request.form.get('excerpt')
            post.published = request.form.get('published') == 'on'
            post.featured = request.form.get('featured') == 'on'
            
            app.logger.info(f"Updated post data: title={post.title}, category_id={post.category_id}, "
                         f"excerpt length={len(post.excerpt) if post.excerpt else 0}, "
                         f"published={post.published}, featured={post.featured}")
            
            # Handle image upload or removal
            image = request.files.get('image')
            remove_image = request.form.get('remove_image') == 'on'
            
            app.logger.info(f"Image file present: {bool(image and image.filename)}")
            app.logger.info(f"Remove image flag: {remove_image}")
            
            if remove_image and post.image:
                app.logger.info(f"Removing image: {post.image}")
                # Remove the current image
                image_path = os.path.join(app.static_folder, 'uploads', post.image)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    app.logger.info(f"Deleted image file: {image_path}")
                post.image = None
            
            if image and image.filename:
                app.logger.info(f"Processing new image: {image.filename}")
                # If there's a current image, delete it
                if post.image:
                    app.logger.info(f"Replacing existing image: {post.image}")
                    old_image_path = os.path.join(app.static_folder, 'uploads', post.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                        app.logger.info(f"Deleted old image file: {old_image_path}")
                
                # Ensure uploads directory exists
                uploads_dir = os.path.join(app.static_folder, 'uploads')
                if not os.path.exists(uploads_dir):
                    app.logger.info(f"Creating uploads directory: {uploads_dir}")
                    os.makedirs(uploads_dir)
                
                filename = secure_filename(image.filename)
                image_path = os.path.join(uploads_dir, filename)
                app.logger.info(f"Saving new image to: {image_path}")
                image.save(image_path)
                post.image = filename
            
            app.logger.info("Committing changes to database")
            db.session.commit()
            
            app.logger.info(f"Post {post_id} updated successfully")
            flash('Gönderi başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_posts'))
            
        return render_template('admin/post_form.html', post=post, categories=categories)
    except Exception as e:
        app.logger.error(f"Edit post error: {str(e)}")
        app.logger.exception("Exception details:")
        flash('Gönderi güncellenirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_posts'))

@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        
        # Delete the image file if it exists
        if post.image:
            image_path = os.path.join(app.static_folder, 'uploads', post.image)
            if os.path.exists(image_path):
                os.remove(image_path)
                app.logger.info(f"Deleted image file: {image_path}")
        
        db.session.delete(post)
        db.session.commit()
        flash('Gönderi başarıyla silindi.', 'success')
    except Exception as e:
        app.logger.error(f"Delete post error: {str(e)}")
        flash('Gönderi silinirken bir hata oluştu.', 'error')
    return redirect(url_for('admin_posts'))

@app.route('/admin/videos')
@login_required
def admin_videos():
    try:
        search_query = request.args.get('search', '')
        if search_query:
            videos = Video.query.filter(
                or_(
                    Video.title.ilike(f'%{search_query}%'),
                    Video.description.ilike(f'%{search_query}%')
                )
            ).order_by(Video.created_at.desc()).all()
        else:
            videos = Video.query.order_by(Video.created_at.desc()).all()
        return render_template('admin/videos.html', videos=videos, search_query=search_query)
    except Exception as e:
        app.logger.error(f"Admin videos error: {str(e)}")
        flash('Videolar yüklenirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/videos/new', methods=['GET', 'POST'])
@login_required
def admin_new_video():
    try:
        if request.method == 'POST':
            title = request.form.get('title')
            youtube_id = request.form.get('youtube_id')
            description = request.form.get('description')
            
            if not title or not youtube_id:
                flash('Başlık ve YouTube ID alanları zorunludur.', 'error')
                return redirect(url_for('admin_new_video'))
            
            video = Video(
                title=title,
                youtube_id=youtube_id,
                description=description,
                thumbnail_url=f'https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg'
            )
            
            db.session.add(video)
            db.session.commit()
            flash('Video başarıyla eklendi.', 'success')
            return redirect(url_for('admin_videos'))
            
        return render_template('admin/video_form.html')
    except Exception as e:
        app.logger.error(f"New video error: {str(e)}")
        flash('Video eklenirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_videos'))

@app.route('/admin/videos/<int:video_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_video(video_id):
    try:
        video = Video.query.get_or_404(video_id)
        
        if request.method == 'POST':
            video.title = request.form.get('title')
            video.youtube_id = request.form.get('youtube_id')
            video.description = request.form.get('description')
            video.thumbnail_url = f'https://img.youtube.com/vi/{video.youtube_id}/maxresdefault.jpg'
            
            db.session.commit()
            flash('Video başarıyla güncellendi.', 'success')
            return redirect(url_for('admin_videos'))
            
        return render_template('admin/video_form.html', video=video)
    except Exception as e:
        app.logger.error(f"Edit video error: {str(e)}")
        flash('Video güncellenirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_videos'))

@app.route('/admin/videos/<int:video_id>/delete', methods=['POST'])
@login_required
def admin_delete_video(video_id):
    try:
        video = Video.query.get_or_404(video_id)
        db.session.delete(video)
        db.session.commit()
        flash('Video başarıyla silindi.', 'success')
    except Exception as e:
        app.logger.error(f"Delete video error: {str(e)}")
        flash('Video silinirken bir hata oluştu.', 'error')
    return redirect(url_for('admin_videos'))

@app.route('/admin/videos/delete/<int:id>')
def delete_video(id):
    video = Video.query.get_or_404(id)
    db.session.delete(video)
    db.session.commit()
    return redirect(url_for('admin_videos'))

@app.route('/category/<slug>')
def category_posts(slug):
    try:
        category = Category.query.filter_by(slug=slug).first_or_404()
        posts = Post.query.filter_by(category_id=category.id).order_by(Post.created_at.desc()).all()
        return render_template('category.html', category=category, posts=posts)
    except Exception as e:
        app.logger.error(f"Category posts error: {str(e)}")
        return render_template('errors/500.html')

@app.context_processor
def inject_categories():
    try:
        categories = Category.query.all()
        return dict(categories=categories)
    except Exception as e:
        app.logger.error(f"Category injection error: {str(e)}")
        return dict(categories=[])

@app.route('/admin/categories', methods=['GET'])
@login_required
def admin_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/new', methods=['POST'])
@login_required
def admin_new_category():
    name = request.form.get('name')
    slug = request.form.get('slug')
    
    if not name or not slug:
        flash('Kategori adı ve slug gereklidir.', 'danger')
        return redirect(url_for('admin_categories'))
    
    # Check if category with same name or slug exists
    exists = Category.query.filter((Category.name == name) | (Category.slug == slug)).first()
    if exists:
        flash('Bu isim veya slug ile bir kategori zaten mevcut.', 'danger')
        return redirect(url_for('admin_categories'))
    
    try:
        category = Category(name=name, slug=slug)
        db.session.add(category)
        db.session.commit()
        flash('Kategori başarıyla oluşturuldu.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Create category error: {str(e)}")
        flash('Kategori oluşturulurken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/edit', methods=['POST'])
@login_required
def admin_edit_category():
    category_id = request.form.get('id')
    name = request.form.get('name')
    slug = request.form.get('slug')
    
    if not name or not slug or not category_id:
        flash('Eksik bilgi.', 'danger')
        return redirect(url_for('admin_categories'))
    
    try:
        category = Category.query.get_or_404(category_id)
        
        # Check if category with same name or slug exists (excluding this one)
        exists = Category.query.filter(
            ((Category.name == name) | (Category.slug == slug)) & 
            (Category.id != category.id)
        ).first()
        
        if exists:
            flash('Bu isim veya slug ile başka bir kategori zaten mevcut.', 'danger')
            return redirect(url_for('admin_categories'))
        
        category.name = name
        category.slug = slug
        db.session.commit()
        flash('Kategori başarıyla güncellendi.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Edit category error: {str(e)}")
        flash('Kategori güncellenirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/<int:id>/delete', methods=['POST'])
@login_required
def admin_delete_category(id):
    try:
        category = Category.query.get_or_404(id)
        
        # Update posts with this category to have no category
        posts = Post.query.filter_by(category_id=id).all()
        for post in posts:
            post.category_id = None
        
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
        comments = Comment.query.order_by(Comment.created_at.desc()).all()
        return render_template('admin/comments.html', comments=comments)
    except Exception as e:
        app.logger.error(f"Admin comments error: {str(e)}")
        flash('Yorumlar yüklenirken bir hata oluştu.', 'danger')
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
        app.logger.error(f"Delete comment error: {str(e)}")
        db.session.rollback()
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
            flash('Tüm alanları doldurun.', 'error')
            return redirect(url_for('admin_settings'))
        
        if new_password != confirm_password:
            flash('Yeni şifreler eşleşmiyor.', 'error')
            return redirect(url_for('admin_settings'))
        
        user = User.query.get(current_user.id)
        if not user.check_password(current_password):
            flash('Mevcut şifre yanlış.', 'error')
            return redirect(url_for('admin_settings'))
        
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Şifreniz başarıyla güncellendi.', 'success')
        return redirect(url_for('admin_settings'))
    except Exception as e:
        app.logger.error(f"Change password error: {str(e)}")
        flash('Şifre değiştirilirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_settings'))

if __name__ == '__main__':
    # Ensure uploads directory exists
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        app.logger.info(f"Created uploads directory at {uploads_dir}")
    
    # Ensure images directory exists for default images
    images_dir = os.path.join(app.static_folder, 'images')
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        app.logger.info(f"Created images directory at {images_dir}")
    
    # Run database migrations if we have a DATABASE_URL (indicating PostgreSQL)
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url and 'postgres' in database_url:
            app.logger.info("PostgreSQL database detected. Running migrations...")
            from migrations import run_migrations
            migration_success = run_migrations()
            if migration_success:
                app.logger.info("Migrations completed successfully")
            else:
                app.logger.error("Migrations failed, but continuing startup")
    except Exception as e:
        app.logger.error(f"Error running migrations: {str(e)}")
        
    # Initialize the database 
    init_db()
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port)
else:
    # This code runs when imported (e.g., by Gunicorn in production)
    # Ensure uploads and images directories exist
    uploads_dir = os.path.join(app.static_folder, 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        app.logger.info(f"Created uploads directory at {uploads_dir}")
    
    images_dir = os.path.join(app.static_folder, 'images')
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        app.logger.info(f"Created images directory at {images_dir}")
    
    # Run database migrations if we have a DATABASE_URL (indicating PostgreSQL)
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url and 'postgres' in database_url:
            app.logger.info("PostgreSQL database detected. Running migrations...")
            from migrations import run_migrations
            migration_success = run_migrations()
            if migration_success:
                app.logger.info("Migrations completed successfully")
            else:
                app.logger.error("Migrations failed, but continuing startup")
    except Exception as e:
        app.logger.error(f"Error running migrations: {str(e)}")
        
    # Initialize the database 
    init_db() 