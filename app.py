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
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Application startup')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f'Page not found: {request.url}')
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'Server Error: {error}')
    return render_template('errors/500.html'), 500

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')

# Get database URL from environment variables with fallback
database_url = os.environ.get('DATABASE_URL', "postgresql://hepsihikaye_wyg3_user:JWWumjYdrR15YATOT4KJvsRz4XxkRxzX@dpg-cvanpdlumphs73ag0b80-a.oregon-postgres.render.com/hepsihikaye_wyg3")

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200), nullable=True)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', lazy=True)

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
            # Drop all tables first
            db.drop_all()
            app.logger.info("Dropped all existing tables")

            # Create all tables
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
        # Get recent posts and videos
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
        
        # Get statistics
        total_posts = Post.query.count()
        total_videos = Video.query.count()
        total_comments = Comment.query.count()
        total_views = db.session.query(db.func.sum(Post.views)).scalar() or 0
        
        return render_template('admin/dashboard.html',
                             posts=recent_posts,
                             videos=recent_videos,
                             total_posts=total_posts,
                             total_videos=total_videos,
                             total_comments=total_comments,
                             total_views=total_views)
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {str(e)}")
        flash('Dashboard yüklenirken bir hata oluştu.', 'error')
        return redirect(url_for('admin_index'))

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
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(6).all()
        recent_videos = Video.query.order_by(Video.created_at.desc()).limit(6).all()
        return render_template('index.html', posts=recent_posts, videos=recent_videos)
    except Exception as e:
        app.logger.error(f"Index page error: {str(e)}")
        return render_template('errors/500.html')

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        post.views += 1
        db.session.commit()
        return render_template('post_detail.html', post=post)
    except Exception as e:
        app.logger.error(f"Post detail error: {str(e)}")
        return render_template('errors/500.html')

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

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port) 