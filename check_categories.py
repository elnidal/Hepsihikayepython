#!/usr/bin/env python3
from app import app, db, Post, CATEGORIES

print("Categories defined in app.py:")
for slug, name in CATEGORIES:
    print(f"  - {slug}: {name}")

with app.app_context():
    posts = Post.query.all()
    print(f"\nFound {len(posts)} posts in database.")
    
    # Count posts by category
    category_counts = {}
    for post in posts:
        if post.category in category_counts:
            category_counts[post.category] += 1
        else:
            category_counts[post.category] = 1
    
    print("\nPosts by category:")
    for category_slug, count in category_counts.items():
        category_name = next((name for slug, name in CATEGORIES if slug == category_slug), category_slug)
        print(f"  - {category_name}: {count} posts")
    
    # Print post details
    print("\nPosts in database:")
    for post in posts:
        print(f"  ID: {post.id}, Title: {post.title} - Category: {post.category}") 