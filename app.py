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

app = Flask(__name__)
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

def init_db():
    db.create_all()
    
    # Check if admin user exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create admin user
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin')
        )
        db.session.add(admin_user)
        db.session.commit()

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
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
        return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    try:
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        recent_videos = Video.query.order_by(Video.created_at.desc()).limit(10).all()
        recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(10).all()
        
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

@app.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        flash('Başarıyla çıkış yaptınız.', 'success')
        return redirect(url_for('admin_login'))
    except Exception as e:
        app.logger.error(f"Logout error: {str(e)}")
        flash('Çıkış yapılırken bir hata oluştu.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port) 