#!/usr/bin/env python3
"""
Script to migrate data from the old database to the new one.
"""
import os
import sys
import json
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from app import User, Post, Comment, Rating, Video, Setting

# Save data from old database
def export_data(old_db_url):
    """Export data from the old database"""
    print(f"Connecting to old database...")
    engine = create_engine(old_db_url, connect_args={"sslmode": "require"})
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Export users
        users = []
        for user in session.query(User).all():
            users.append({
                'id': user.id,
                'username': user.username,
                'password': user.password
            })
        print(f"Exported {len(users)} users")
        
        # Export posts
        posts = []
        for post in session.query(Post).all():
            posts.append({
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'category': post.category,
                'author': post.author,
                'image_url': post.image_url,
                'created_at': post.created_at.isoformat() if post.created_at else None,
                'likes': post.likes,
                'dislikes': post.dislikes
            })
        print(f"Exported {len(posts)} posts")
        
        # Export comments
        comments = []
        for comment in session.query(Comment).all():
            comments.append({
                'id': comment.id,
                'post_id': comment.post_id,
                'name': comment.name,
                'email': comment.email,
                'content': comment.content,
                'created_at': comment.created_at.isoformat() if comment.created_at else None,
                'is_approved': comment.is_approved,
                'ip_address': comment.ip_address
            })
        print(f"Exported {len(comments)} comments")
        
        # Export ratings
        ratings = []
        for rating in session.query(Rating).all():
            ratings.append({
                'id': rating.id,
                'post_id': rating.post_id,
                'ip_address': rating.ip_address,
                'is_like': rating.is_like,
                'created_at': rating.created_at.isoformat() if rating.created_at else None
            })
        print(f"Exported {len(ratings)} ratings")
        
        # Export videos
        videos = []
        for video in session.query(Video).all():
            videos.append({
                'id': video.id,
                'title': video.title,
                'youtube_embed': video.youtube_embed,
                'created_at': video.created_at.isoformat() if video.created_at else None
            })
        print(f"Exported {len(videos)} videos")
        
        # Export settings
        settings = []
        for setting in session.query(Setting).all():
            settings.append({
                'id': setting.id,
                'key': setting.key,
                'value': setting.value,
                'updated_at': setting.updated_at.isoformat() if setting.updated_at else None
            })
        print(f"Exported {len(settings)} settings")
        
        # Create data object
        data = {
            'users': users,
            'posts': posts,
            'comments': comments,
            'ratings': ratings,
            'videos': videos,
            'settings': settings
        }
        
        # Save to file
        with open('database_export.json', 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Data exported to database_export.json")
        return data
        
    except Exception as e:
        print(f"Error exporting data: {str(e)}")
        return None
    finally:
        session.close()

# Import data to new database
def import_data(new_db_url, data=None):
    """Import data to the new database"""
    if data is None:
        try:
            with open('database_export.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print("Error: database_export.json not found")
            return False
    
    print(f"Connecting to new database...")
    from app import app, db
    
    try:
        with app.app_context():
            # Import users (skip if id already exists)
            for user_data in data['users']:
                user_id = user_data['id']
                if not User.query.get(user_id):
                    user = User(
                        id=user_id,
                        username=user_data['username'],
                        password=user_data['password']
                    )
                    db.session.add(user)
            
            # Import posts
            for post_data in data['posts']:
                post_id = post_data['id']
                if not Post.query.get(post_id):
                    post = Post(
                        id=post_id,
                        title=post_data['title'],
                        content=post_data['content'],
                        category=post_data['category'],
                        author=post_data['author'],
                        image_url=post_data['image_url'],
                        created_at=datetime.fromisoformat(post_data['created_at']) if post_data['created_at'] else None,
                        likes=post_data['likes'],
                        dislikes=post_data['dislikes']
                    )
                    db.session.add(post)
            
            # Import comments
            for comment_data in data['comments']:
                comment_id = comment_data['id']
                if not Comment.query.get(comment_id):
                    comment = Comment(
                        id=comment_id,
                        post_id=comment_data['post_id'],
                        name=comment_data['name'],
                        email=comment_data['email'],
                        content=comment_data['content'],
                        created_at=datetime.fromisoformat(comment_data['created_at']) if comment_data['created_at'] else None,
                        is_approved=comment_data['is_approved'],
                        ip_address=comment_data['ip_address']
                    )
                    db.session.add(comment)
            
            # Import ratings
            for rating_data in data['ratings']:
                rating_id = rating_data['id']
                if not Rating.query.get(rating_id):
                    rating = Rating(
                        id=rating_id,
                        post_id=rating_data['post_id'],
                        ip_address=rating_data['ip_address'],
                        is_like=rating_data['is_like'],
                        created_at=datetime.fromisoformat(rating_data['created_at']) if rating_data['created_at'] else None
                    )
                    db.session.add(rating)
            
            # Import videos
            for video_data in data['videos']:
                video_id = video_data['id']
                if not Video.query.get(video_id):
                    video = Video(
                        id=video_id,
                        title=video_data['title'],
                        youtube_embed=video_data['youtube_embed'],
                        created_at=datetime.fromisoformat(video_data['created_at']) if video_data['created_at'] else None
                    )
                    db.session.add(video)
            
            # Import settings
            for setting_data in data['settings']:
                setting_id = setting_data['id']
                if not Setting.query.get(setting_id):
                    setting = Setting(
                        id=setting_id,
                        key=setting_data['key'],
                        value=setting_data['value'],
                        updated_at=datetime.fromisoformat(setting_data['updated_at']) if setting_data['updated_at'] else None
                    )
                    db.session.add(setting)
            
            # Commit changes
            db.session.commit()
            print("Data import completed successfully")
            return True
            
    except Exception as e:
        print(f"Error importing data: {str(e)}")
        return False

if __name__ == "__main__":
    # Get database URLs
    old_db_url = os.environ.get('OLD_DATABASE_URL')
    new_db_url = os.environ.get('DATABASE_URL')
    
    if not old_db_url:
        print("Error: OLD_DATABASE_URL environment variable not set")
        sys.exit(1)
    
    if not new_db_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Export data
    data = export_data(old_db_url)
    
    if data:
        # Import data
        success = import_data(new_db_url, data)
        sys.exit(0 if success else 1)
    else:
        sys.exit(1) 