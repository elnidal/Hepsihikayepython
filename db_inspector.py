#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone
from app import app, db, Post
import sqlalchemy

def main():
    print("=" * 50)
    print("DATABASE INSPECTOR TOOL")
    print("=" * 50)
    
    # Check environment
    print("\nEnvironment:")
    print(f"DATABASE_URL: {'*****' if os.environ.get('DATABASE_URL') else 'Not set (using default)'}")
    print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'Not set')}")
    print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else '(hidden)'}")
    
    # Try connecting to the database
    print("\nTesting database connection...")
    try:
        with app.app_context():
            connection = db.engine.connect()
            print("✅ Successfully connected to the database")
            connection.close()
    except Exception as e:
        print(f"❌ Failed to connect to database: {str(e)}")
        return
    
    # Check table existence
    print("\nChecking database tables...")
    with app.app_context():
        inspector = sqlalchemy.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        if 'post' not in tables:
            print("❌ The 'post' table does not exist!")
            return
    
    # Count posts
    print("\nCounting posts...")
    with app.app_context():
        try:
            post_count = Post.query.count()
            print(f"Found {post_count} posts in the database")
            
            if post_count > 0:
                # Get some post data
                posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
                print("\nLatest posts:")
                for i, post in enumerate(posts):
                    created_at = post.created_at.strftime("%Y-%m-%d %H:%M:%S") if post.created_at else "None"
                    print(f"{i+1}. ID: {post.id}, Title: {post.title[:40]}..., Created: {created_at}")
                    print(f"   Category: {post.category}, Image: {'Yes' if post.image_url else 'No'}")
            else:
                print("❌ No posts found in the database!")
                
                # Check if we can create a test post
                print("\nAttempting to create a test post...")
                test_post = Post(
                    title="Test Post - Please Delete",
                    content="This is a test post created to verify database functionality.",
                    category="öykü",
                    author="System",
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(test_post)
                db.session.commit()
                print(f"✅ Successfully created test post with ID: {test_post.id}")
                
                # Verify it exists
                post_count = Post.query.count()
                print(f"Now found {post_count} posts in the database")
        except Exception as e:
            print(f"❌ Error querying posts: {str(e)}")
    
    # Try to determine database URL origin
    print("\nDatabase URL source:")
    if os.environ.get('DATABASE_URL'):
        print("Using DATABASE_URL from environment variable")
    else:
        print("Using fallback DATABASE_URL hardcoded in app.py")
    
    print("\nRecommendations:")
    print("1. Make sure DATABASE_URL is correctly set in environment variables")
    print("2. Check if database migrations have been run to create tables")
    print("3. Verify that posts are being properly saved (check create/edit routes)")
    print("4. Ensure the database server is stable and not intermittently failing")

if __name__ == "__main__":
    main() 