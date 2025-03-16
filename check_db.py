#!/usr/bin/env python3
from app import app, db, Post, CATEGORIES

with app.app_context():
    # Check post count
    total_posts = Post.query.count()
    print(f"Total posts in database: {total_posts}")
    
    # Check categories setup
    print("\nCategories defined in app:")
    for slug, name in CATEGORIES:
        print(f" - {slug}: {name}")
    
    # Check posts in database
    print("\nSample posts:")
    posts = Post.query.limit(5).all()
    for post in posts:
        print(f" - ID: {post.id}, Title: {post.title}, Category: {post.category}")
    
    # Check category counts
    print("\nCategory counts:")
    for slug, name in CATEGORIES:
        count = Post.query.filter_by(category=slug).count()
        print(f" - {name}: {count} posts") 