from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect, FlaskForm
from flask_ckeditor import CKEditor, CKEditorField
import os
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired
from sqlalchemy import or_

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
ckeditor = CKEditor(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostAdmin(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    form_overrides = {
        'content': CKEditorField
    }

    form_extra_fields = {
        'category': SelectField('Category', choices=CATEGORIES)
    }

    column_list = ('title', 'category', 'created_at')
    form_columns = ('title', 'content', 'category')

    create_template = 'admin/create_post.html'
    edit_template = 'admin/edit_post.html'

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    youtube_embed = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    # Get latest posts
    latest_posts = Post.query.order_by(Post.created_at.desc()).limit(4).all()
    
    # Get featured posts (for now, just getting some recent posts)
    featured_posts = Post.query.order_by(Post.created_at.desc()).limit(3).all()
    
    return render_template('index.html', 
                         latest_posts=latest_posts,
                         featured_posts=featured_posts,
                         current_year=datetime.now().year,
                         active_category=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        print(f"Login attempt for user: {username}")  # Debug log
        
        user = User.query.filter_by(username=username).first()
        print(f"User found: {user is not None}")  # Debug log
        
        if user and check_password_hash(user.password, password):
            print("Password check successful")  # Debug log
            login_user(user)
            flash('Başarıyla giriş yaptınız!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('admin.index'))
        else:
            print("Password check failed")  # Debug log
            flash('Geçersiz kullanıcı adı veya şifre!', 'error')
    
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

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    f = request.files.get('upload')
    if not f:
        return jsonify({'error': {'message': 'No file uploaded'}})

    # Check if the file is an allowed image type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if '.' not in f.filename or f.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'error': {'message': 'Invalid file type'}})

    # Save the file with a unique name
    filename = secure_filename(f.filename)
    unique_filename = datetime.now().strftime('%Y%m%d_%H%M%S_') + filename
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
    
    # Return the URL
    url = url_for('static', filename=f'uploads/{unique_filename}')
    return jsonify({'url': url})

def create_admin_user(username, password):
    print(f"Creating admin user: {username}")  # Debug log
    with app.app_context():
        # Check if admin user already exists
        admin = User.query.filter_by(username=username).first()
        if not admin:
            print(f"Admin user does not exist, creating new one")  # Debug log
            admin = User(
                username=username,
                password=generate_password_hash(password, method='sha256')
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user created successfully")  # Debug log
        else:
            print(f"Admin user already exists")  # Debug log
            # Update password if needed
            admin.password = generate_password_hash(password, method='sha256')
            db.session.commit()
            print(f"Admin password updated")  # Debug log

@app.before_first_request
def initialize_app():
    print("Initializing application...")  # Debug log
    db.create_all()
    admin_username = os.environ.get('ADMIN_USERNAME', 'elnidal')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'm37479673m')
    create_admin_user(admin_username, admin_password)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
