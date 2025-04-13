from flask import jsonify, request, Blueprint, current_app
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import jwt
from app import db, User, Post, Category, Comment, Video
import os
import logging
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup

# Create Blueprint for mobile API
mobile_api = Blueprint('mobile_api', __name__, url_prefix='/api/v1')

# Setup logging
logger = logging.getLogger('mobile_api')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'hepsihikaye-mobile-dev-key')
JWT_EXPIRATION = 60 * 60 * 24 * 7  # 7 days

# Token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing', 'status': 'error'}), 401
        
        try:
            # Decode token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']
            current_user = User.query.get(current_user_id)
            
            if not current_user:
                return jsonify({'message': 'Invalid token', 'status': 'error'}), 401
                
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return jsonify({'message': 'Invalid token', 'status': 'error'}), 401
            
        return f(current_user, *args, **kwargs)
        
    return decorated

# Standard API response format
def api_response(data=None, status=200, message="Success"):
    response = {
        "status": "success" if status < 400 else "error",
        "message": message,
        "data": data
    }
    return jsonify(response), status

# Authentication routes
@mobile_api.route('/auth/login', methods=['POST'])
def mobile_admin_login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return api_response(message="Username and password are required", status=400)
        
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user or not user.check_password(data.get('password')):
        return api_response(message="Invalid credentials", status=401)
    
    # Generate token
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    }, JWT_SECRET_KEY, algorithm="HS256")
    
    return api_response({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username
        },
        'expires_in': JWT_EXPIRATION
    })

@mobile_api.route('/auth/refresh', methods=['POST'])
@token_required
def refresh_token(current_user):
    # Generate new token
    token = jwt.encode({
        'user_id': current_user.id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    }, JWT_SECRET_KEY, algorithm="HS256")
    
    return api_response({
        'token': token,
        'expires_in': JWT_EXPIRATION
    })

# Posts routes
@mobile_api.route('/posts', methods=['GET'])
@token_required
def mobile_get_posts(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id', type=int)
    featured = request.args.get('featured', type=bool)
    
    query = Post.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if featured is not None:
        query = query.filter_by(featured=featured)
    
    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page)
    
    result = {
        'items': [{
            'id': post.id,
            'title': post.title,
            'excerpt': post.excerpt or (BeautifulSoup(post.content, 'html.parser').get_text()[:150] + '...' if len(BeautifulSoup(post.content, 'html.parser').get_text()) > 150 else BeautifulSoup(post.content, 'html.parser').get_text()),
            'category_id': post.category_id,
            'category_name': post.category.name if post.category else None,
            'created_at': post.created_at.isoformat(),
            'views': post.views,
            'likes': post.likes,
            'published': post.published,
            'featured': post.featured,
            'image': post.image
        } for post in posts.items],
        'page': posts.page,
        'pages': posts.pages,
        'total': posts.total
    }
    
    return api_response(result)

@mobile_api.route('/posts/<int:post_id>', methods=['GET'])
@token_required
def mobile_get_post(current_user, post_id):
    post = Post.query.get_or_404(post_id)
    
    result = {
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'excerpt': post.excerpt,
        'category_id': post.category_id,
        'category_name': post.category.name if post.category else None,
        'author_id': post.author_id,
        'author_username': post.author_relationship.username if post.author_relationship else None,
        'created_at': post.created_at.isoformat(),
        'updated_at': post.updated_at.isoformat() if post.updated_at else None,
        'views': post.views,
        'likes': post.likes,
        'dislikes': post.dislikes,
        'published': post.published,
        'featured': post.featured,
        'image': post.image,
        'comments': [{
            'id': comment.id,
            'content': comment.content,
            'name': comment.name,
            'created_at': comment.created_at.isoformat(),
            'status': comment.status
        } for comment in post.comments]
    }
    
    return api_response(result)

@mobile_api.route('/posts', methods=['POST'])
@token_required
def mobile_create_post(current_user):
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('content'):
        return api_response(message="Title and content are required", status=400)
    
    category_id = data.get('category_id')
    if category_id:
        category = Category.query.get(category_id)
        if not category:
            return api_response(message="Invalid category", status=400)
            
    # Get author_id from request, assuming it might be passed
    # Or potentially default to the current_user if that makes sense for your API auth
    author_id = data.get('author_id') 
    
    post = Post(
        title=data.get('title'),
        content=data.get('content'),
        excerpt=data.get('excerpt'),
        category_id=category_id,
        published=data.get('published', True),
        featured=data.get('featured', False),
        author_id=author_id, # Use the new author_id
        image=data.get('image') # Assuming image URL might be passed
    )
    
    db.session.add(post)
    db.session.commit()
    
    return api_response({'id': post.id, 'title': post.title}, status=201, message="Post created successfully")

@mobile_api.route('/posts/<int:post_id>', methods=['PUT'])
@token_required
def mobile_update_post(current_user, post_id):
    post = Post.query.get_or_404(post_id)
    data = request.get_json()
    
    if not data:
        return api_response(message="Request body cannot be empty", status=400)
        
    # Update fields if present in the request
    if 'title' in data: post.title = data['title']
    if 'content' in data: post.content = data['content']
    if 'excerpt' in data: post.excerpt = data['excerpt']
    if 'category_id' in data:
        category_id = data['category_id']
        if category_id:
             category = Category.query.get(category_id)
             if not category:
                 return api_response(message="Invalid category", status=400)
             post.category_id = category_id
        else:
             post.category_id = None
             
    if 'published' in data: post.published = data['published']
    if 'featured' in data: post.featured = data['featured']
    # Update author_id if provided
    if 'author_id' in data: post.author_id = data['author_id']
    if 'image' in data: post.image = data['image'] # Assuming image URL might be passed
    
    db.session.commit()
    
    return api_response({'id': post.id, 'title': post.title}, message="Post updated successfully")

@mobile_api.route('/posts/<int:post_id>', methods=['DELETE'])
@token_required
def mobile_delete_post(current_user, post_id):
    post = Post.query.get_or_404(post_id)
    
    db.session.delete(post)
    db.session.commit()
    
    return api_response(message="Post deleted successfully")

# Category routes
@mobile_api.route('/categories', methods=['GET'])
@token_required
def mobile_get_categories(current_user):
    categories = Category.query.all()
    
    result = [{
        'id': category.id,
        'name': category.name,
        'slug': category.slug,
        'post_count': len(category.posts)
    } for category in categories]
    
    return api_response(result)

# Comments routes
@mobile_api.route('/comments', methods=['GET'])
@token_required
def mobile_get_comments(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    
    query = Comment.query
    
    if status:
        query = query.filter_by(status=status)
    
    comments = query.order_by(Comment.created_at.desc()).paginate(page=page, per_page=per_page)
    
    result = {
        'items': [{
            'id': comment.id,
            'content': comment.content,
            'name': comment.name,
            'email': comment.email,
            'created_at': comment.created_at.isoformat(),
            'status': comment.status,
            'post_id': comment.post_id,
            'post_title': comment.post.title if comment.post else None,
            'video_id': comment.video_id,
            'video_title': comment.video.title if comment.video else None
        } for comment in comments.items],
        'page': comments.page,
        'pages': comments.pages,
        'total': comments.total
    }
    
    return api_response(result)

@mobile_api.route('/comments/<int:comment_id>', methods=['PUT'])
@token_required
def mobile_update_comment_status(current_user, comment_id):
    comment = Comment.query.get_or_404(comment_id)
    data = request.get_json()
    
    if 'status' in data:
        if data['status'] not in ['pending', 'approved', 'rejected']:
            return api_response(message="Invalid status", status=400)
        comment.status = data['status']
    
    db.session.commit()
    
    return api_response(message="Comment status updated")

# Statistics endpoints
@mobile_api.route('/stats/overview', methods=['GET'])
@token_required
def mobile_get_stats_overview(current_user):
    # Get post count
    post_count = Post.query.count()
    
    # Get view count
    view_count = db.session.query(db.func.sum(Post.views)).scalar() or 0
    
    # Get comment count
    comment_count = Comment.query.count()
    
    # Get like count
    like_count = db.session.query(db.func.sum(Post.likes)).scalar() or 0
    
    # Get video count
    video_count = Video.query.count()
    
    # Get category count
    category_count = Category.query.count()
    
    # Get recent posts
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    recent_post_data = [{
        'id': post.id,
        'title': post.title,
        'created_at': post.created_at.isoformat(),
        'views': post.views
    } for post in recent_posts]
    
    # Get top posts by views
    top_posts = Post.query.order_by(Post.views.desc()).limit(5).all()
    top_post_data = [{
        'id': post.id,
        'title': post.title,
        'views': post.views
    } for post in top_posts]
    
    result = {
        'counts': {
            'posts': post_count,
            'views': view_count,
            'comments': comment_count,
            'likes': like_count,
            'videos': video_count,
            'categories': category_count
        },
        'recent_posts': recent_post_data,
        'top_posts': top_post_data
    }
    
    return api_response(result)

# Media upload
@mobile_api.route('/media/upload', methods=['POST'])
@token_required
def mobile_upload_media(current_user):
    if 'file' not in request.files:
        return api_response(message="No file part", status=400)
    
    file = request.files['file']
    
    if file.filename == '':
        return api_response(message="No selected file", status=400)
    
    folder = request.form.get('folder', 'posts')
    
    # Upload to Supabase or local folder based on app config
    from app import upload_to_supabase
    
    try:
        if hasattr(current_app, 'config') and current_app.config.get('SUPABASE_URL'):
            # Upload to Supabase
            url = upload_to_supabase(file, folder)
            if url:
                return api_response({'url': url}, message="File uploaded successfully")
            else:
                return api_response(message="Failed to upload file to Supabase", status=500)
        else:
            # Local upload
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            new_filename = f"{timestamp}_{filename}"
            
            upload_folder = os.path.join(current_app.static_folder, 'uploads', folder)
            
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
                
            file_path = os.path.join(upload_folder, new_filename)
            file.save(file_path)
            
            url = url_for('static', filename=f'uploads/{folder}/{new_filename}', _external=True)
            return api_response({'url': url}, message="File uploaded successfully")
            
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return api_response(message=f"Upload failed: {str(e)}", status=500)

@mobile_api.route('/feed', methods=['GET'])
@token_required
def mobile_get_feed(current_user):
    """Get the latest posts in a format optimized for the iOS app."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category_id = request.args.get('category_id', type=int)
    
    query = Post.query.filter_by(published=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page)
    
    result = {
        'items': [{
            'id': item.id,
            'type': 'post' if isinstance(item, Post) else 'video',
            'title': item.title,
            'excerpt': getattr(item, 'excerpt', None) or (BeautifulSoup(getattr(item, 'content', ''), 'html.parser').get_text()[:150] + '...' if len(BeautifulSoup(getattr(item, 'content', ''), 'html.parser').get_text()) > 150 else BeautifulSoup(getattr(item, 'content', ''), 'html.parser').get_text()),
            'category_id': item.category_id,
            'category_name': item.category.name if item.category else None,
            'created_at': item.created_at.isoformat(),
            'views': getattr(item, 'views', 0),
            'likes': getattr(item, 'likes', 0),
            'published': item.published,
            'featured': getattr(item, 'featured', False),
            'image': getattr(item, 'image', None),
            'author_id': getattr(item, 'author_id', None) if isinstance(item, Post) else None,
            'author_username': getattr(item.author_relationship, 'username', None) if isinstance(item, Post) and hasattr(item, 'author_relationship') else None
        } for item in posts.items],
        'page': posts.page,
        'pages': posts.pages,
        'total': posts.total
    }
    
    return api_response(result)

@mobile_api.route('/public/feed', methods=['GET'])
def mobile_get_public_feed():
    """Get the latest public posts for the iOS app without requiring authentication."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    category_id = request.args.get('category_id', type=int)
    
    query = Post.query.filter_by(published=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    posts = query.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page)
    
    result = {
        'items': [{
            'id': item.id,
            'type': 'post' if isinstance(item, Post) else 'video',
            'title': item.title,
            'excerpt': getattr(item, 'excerpt', None) or (BeautifulSoup(getattr(item, 'content', ''), 'html.parser').get_text()[:150] + '...' if len(BeautifulSoup(getattr(item, 'content', ''), 'html.parser').get_text()) > 150 else BeautifulSoup(getattr(item, 'content', ''), 'html.parser').get_text()),
            'category_id': item.category_id,
            'category_name': item.category.name if item.category else None,
            'created_at': item.created_at.isoformat(),
            'views': getattr(item, 'views', 0),
            'likes': getattr(item, 'likes', 0),
            'published': item.published,
            'featured': getattr(item, 'featured', False),
            'image': getattr(item, 'image', None),
            'author_id': getattr(item, 'author_id', None) if isinstance(item, Post) else None,
            'author_username': getattr(item.author_relationship, 'username', None) if isinstance(item, Post) and hasattr(item, 'author_relationship') else None
        } for item in posts.items],
        'page': posts.page,
        'pages': posts.pages,
        'total': posts.total
    }
    
    return api_response(result)

@mobile_api.route('/public/post/<int:post_id>', methods=['GET'])
def mobile_get_public_post(post_id):
    """Get a single public post with full content without requiring authentication."""
    post = Post.query.filter_by(id=post_id, published=True).first_or_404()
    
    # Increment view count
    post.views += 1
    db.session.commit()
    
    result = {
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'excerpt': post.excerpt,
        'category_id': post.category_id,
        'category_name': post.category.name if post.category else None,
        'author_id': post.author_id,
        'author_username': post.author_relationship.username if post.author_relationship else None,
        'created_at': post.created_at.isoformat(),
        'updated_at': post.updated_at.isoformat() if post.updated_at else None,
        'views': post.views,
        'likes': post.likes,
        'dislikes': post.dislikes,
        'image': post.image,
        'enclosure': {
            'url': post.image if post.image and post.image.startswith('http') else f"{request.url_root.rstrip('/')}/static/uploads/{post.image}" if post.image else None,
            'type': 'image/jpeg',
            'length': 0
        } if post.image else None,
        'comments': [{
            'id': comment.id,
            'content': comment.content,
            'name': comment.name,
            'created_at': comment.created_at.isoformat(),
            'status': comment.status
        } for comment in post.comments if comment.status == 'approved']
    }
    
    return api_response(result)

# Register the blueprint with the app
def register_mobile_api(app):
    app.register_blueprint(mobile_api)
    logger.info("Mobile API registered") 