#!/usr/bin/env python3
import os
import random
from app import app, Post, db

def main():
    """Fix missing image_url values for posts"""
    print("=== Image Fix Utility ===")
    
    # Get available images
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        print(f"❌ Upload directory does not exist: {upload_dir}")
        return
    
    available_images = [f for f in os.listdir(upload_dir) 
                       if os.path.isfile(os.path.join(upload_dir, f)) and 
                       not f.startswith('.')]
    
    if not available_images:
        print("❌ No image files found in the upload directory")
        return
    
    print(f"Found {len(available_images)} available images")
    
    # Get posts without images
    with app.app_context():
        posts = Post.query.filter(Post.image_url.is_(None)).all()
        posts_with_images = Post.query.filter(Post.image_url.isnot(None)).all()
        
        print(f"Found {len(posts)} posts without images")
        print(f"Found {len(posts_with_images)} posts with images already set")
        
        if not posts:
            print("No posts need image fixes.")
            return
        
        # Assign images to posts
        print("\nAssigning images to posts...")
        
        for i, post in enumerate(posts):
            # Cycle through available images
            img_index = i % len(available_images)
            image_filename = available_images[img_index]
            
            print(f"Assigning {image_filename} to post: {post.title[:40]}...")
            post.image_url = image_filename
        
        # Commit changes
        db.session.commit()
        print("\n✅ Successfully updated image_url for posts")

if __name__ == "__main__":
    main() 