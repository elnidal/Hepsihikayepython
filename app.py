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
import time
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired
from sqlalchemy import or_

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("blog.db")}'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['CKEDITOR_FILE_UPLOADER'] = 'upload'

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
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostAdmin(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    form_overrides = {
        'content': CKEditorField
    }
    column_list = ('title', 'category', 'created_at')
    form_columns = ('title', 'content', 'category', 'image_url')
    form_choices = {'category': CATEGORIES}

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/debug/check-admin')
def check_admin():
    try:
        # Check if database exists
        if not os.path.exists('blog.db'):
            return jsonify({
                'status': 'error',
                'message': 'Database file does not exist',
                'db_path': os.path.abspath('blog.db')
            })

        # Check admin user
        admin = User.query.filter_by(username='elnidal').first()
        if admin:
            return jsonify({
                'status': 'success',
                'message': 'Admin user found',
                'details': {
                    'username': admin.username,
                    'id': admin.id,
                    'password_hash': admin.password[:10] + '...'  # Show only first 10 chars of hash
                }
            })
        else:
            # List all users in database
            all_users = User.query.all()
            return jsonify({
                'status': 'error',
                'message': 'Admin user not found',
                'existing_users': [{'id': u.id, 'username': u.username} for u in all_users]
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error checking admin user: {str(e)}'
        })

@app.route('/debug/init-admin')
def init_admin():
    try:
        with app.app_context():
            # Create admin user
            admin_username = 'elnidal'
            admin_password = 'm37479673m'
            
            admin = User.query.filter_by(username=admin_username).first()
            if admin:
                admin.password = generate_password_hash(admin_password, method='sha256')
                db.session.commit()
                message = 'Admin password updated'
            else:
                admin = User(
                    username=admin_username,
                    password=generate_password_hash(admin_password, method='sha256')
                )
                db.session.add(admin)
                db.session.commit()
                message = 'Admin user created'
                
            return jsonify({
                'status': 'success',
                'message': message,
                'username': admin_username
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error initializing admin: {str(e)}'
        })

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
