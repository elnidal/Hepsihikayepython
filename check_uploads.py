#!/usr/bin/env python3
import os
from app import app, Post, db
import sys

def main():
    """Check image paths and file existence"""
    print("=== Image Path Diagnostics ===")
    
    # Print configuration
    print("\nConfiguration:")
    print(f"UPLOAD_FOLDER: {app.config['UPLOAD_FOLDER']}")
    print(f"UPLOAD_URL: {app.config['UPLOAD_URL']}")
    print(f"IS_PRODUCTION: {app.config['IS_PRODUCTION']}")
    print(f"STATIC_FOLDER: {app.static_folder}")

    # Check if upload directory exists
    upload_dir = app.config['UPLOAD_FOLDER']
    print(f"\nChecking upload directory: {upload_dir}")
    if os.path.exists(upload_dir):
        print(f"✅ Upload directory exists")
        files = os.listdir(upload_dir)
        print(f"Files in upload directory: {len(files)}")
        if files:
            print("Sample files:")
            for f in files[:5]:
                print(f"  - {f}")
    else:
        print(f"❌ Upload directory does not exist")
        
    # Check alternate paths
    static_uploads = os.path.join(app.static_folder, 'uploads')
    print(f"\nChecking static/uploads directory: {static_uploads}")
    if os.path.exists(static_uploads):
        print(f"✅ Static uploads directory exists")
        files = os.listdir(static_uploads)
        print(f"Files in static/uploads: {len(files)}")
        if files:
            print("Sample files:")
            for f in files[:5]:
                print(f"  - {f}")
    else:
        print(f"❌ Static uploads directory does not exist")

    # Check posts with images
    print("\nPosts with images:")
    with app.app_context():
        posts = Post.query.filter(Post.image_url.isnot(None)).all()
        print(f"Found {len(posts)} posts with image_url set")
        
        if posts:
            print("\nChecking image files for first 5 posts:")
            for i, post in enumerate(posts[:5]):
                print(f"\nPost {i+1}: {post.title}")
                print(f"  image_url: {post.image_url}")
                
                # Check if file exists in upload directory
                upload_path = os.path.join(upload_dir, post.image_url)
                static_path = os.path.join(static_uploads, post.image_url)
                
                print(f"  upload path: {upload_path}")
                print(f"  exists: {os.path.exists(upload_path)}")
                
                print(f"  static path: {static_path}")
                print(f"  exists: {os.path.exists(static_path)}")
                
                # Get URL from method
                with app.test_request_context():
                    url = post.get_image_url()
                    print(f"  get_image_url(): {url}")

if __name__ == "__main__":
    main() 