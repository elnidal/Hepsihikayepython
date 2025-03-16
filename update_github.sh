#!/bin/bash

# Update GitHub with all the changes made to fix disappearing posts issue

echo "===== Updating GitHub Repository ====="

# Add modified files
echo "Adding modified files..."
git add app.py
git add templates/index.html
git add templates/category.html
git add templates/post.html
git add templates/post_detail.html
git add requirements.txt

# Add new diagnostic files
echo "Adding new diagnostic files..."
git add db_inspector.py
git add add_sample_posts.py
git add db_persistent_check.py
git add test_image.html
git add update_github.sh
git add prod_debug.py

# Commit the changes
echo "Committing changes..."
git commit -m "Add production debugging tools and improved error logging"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "If you see any errors above, please resolve them before proceeding." 