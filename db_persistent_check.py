#!/usr/bin/env python3
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from app import app, db, Post

def check_db_url():
    """Check the database URL configuration"""
    print("\nDatabase URL Configuration:")
    
    # Get the database URL
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    db_url_env = os.environ.get('DATABASE_URL', 'Not set')
    
    # Parse the URL to extract components
    parsed = urlparse(db_url)
    
    print(f"Using database type: {parsed.scheme}")
    print(f"Host: {parsed.hostname}")
    
    # Check if DATABASE_URL is set in environment
    if 'DATABASE_URL' in os.environ:
        print("✅ DATABASE_URL environment variable is set")
    else:
        print("⚠️ DATABASE_URL environment variable is NOT set")
        print("  Using fallback value from app.py")
    
    # Check if using production URL
    if 'render.com' in db_url:
        print("✅ Using Render.com hosted database")
    else:
        print("⚠️ Not using Render.com hosted database")
    
    # Check if using SSL
    if app.config['SQLALCHEMY_ENGINE_OPTIONS'].get('connect_args', {}).get('sslmode') == 'require':
        print("✅ SSL connection is required")
    else:
        print("⚠️ SSL connection is not required")

def check_persistence():
    """Check if we can create a post and if it persists after restart"""
    print("\nChecking Database Persistence:")
    
    marker = f"persistence-test-{int(time.time())}"
    
    with app.app_context():
        # Create a test post with unique marker
        test_post = Post(
            title=f"Persistence Test - {marker}",
            content=f"<p>This is a test post with marker {marker} created for testing database persistence.</p>",
            category="öykü",
            author="System",
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(test_post)
        db.session.commit()
        post_id = test_post.id
        
        print(f"Created test post with ID {post_id} and marker {marker}")
        
        # Check if it exists immediately
        if Post.query.filter_by(id=post_id).first():
            print("✅ Test post exists immediately after creation")
        else:
            print("❌ Test post does NOT exist immediately after creation!")
        
        # Simulate a short delay
        print("Waiting 2 seconds to simulate time passing...")
        time.sleep(2)
        
        # Check if it still exists after a short delay
        db.session.expire_all()  # Clear SQLAlchemy cache
        if Post.query.filter_by(id=post_id).first():
            print("✅ Test post exists after a short delay")
        else:
            print("❌ Test post does NOT exist after a short delay!")
        
        # Count existing posts
        post_count = Post.query.count()
        print(f"Total posts in database: {post_count}")
        
        # Find posts created in the last day
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_posts = Post.query.filter(Post.created_at >= yesterday).count()
        print(f"Posts created in the last 24 hours: {recent_posts}")

def recommend_fixes():
    """Recommend fixes based on findings"""
    print("\nRecommendations to Fix Disappearing Posts:")
    print("1. Ensure DATABASE_URL is correctly set in both:")
    print("   - Local .env file for development")
    print("   - Render.com environment variables for production")
    
    print("\n2. Check the database connection in app.py:")
    print("   - Make sure SSL is required for Render.com databases")
    print("   - Verify the hostname includes full domain (oregon-postgres.render.com)")
    
    print("\n3. Add robust error handling in routes that create/edit posts:")
    print("   - Log database errors")
    print("   - Display user-friendly messages when errors occur")
    
    print("\n4. Consider implementing database backups:")
    print("   - Scheduled PostgreSQL dumps")
    print("   - Verify backup restoration works properly")

def main():
    print("=" * 50)
    print("DATABASE PERSISTENCE DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Check the database URL configuration
    check_db_url()
    
    # Check database persistence
    check_persistence()
    
    # Recommend fixes
    recommend_fixes()

if __name__ == "__main__":
    main() 