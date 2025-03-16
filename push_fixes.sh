#!/bin/bash

echo "========================================================"
echo "  Pushing all fixes to GitHub for HepsiHikaye Website   "
echo "========================================================"
echo

echo "Adding files to Git..."
git add static/uploads/default_post_image.png
git add static/uploads/README.md
git add fix_render_uploads.py
git add fix_categories_and_images.py
git add fix_app_categories.py
git add check_db_categories.py
git add create_default_image.py
git add push_fixes.sh
git add app.py

echo "Committing changes..."
git commit -m "Fix: Image paths, categories display, and uploads handling

- Fixed image paths to use static/uploads directory
- Modified app to show all categories in navigation
- Added default image for posts without images
- Updated serve_upload route to use static files
- Fixed get_image_url method to handle missing images
- Added comprehensive logging for all operations"

echo "Pushing to GitHub..."
git push origin main

echo
echo "========================================================"
echo "All fixes pushed to GitHub!"
echo "The website will automatically deploy on Render.com"
echo "Your website should now show ALL categories and display"
echo "images correctly, even in production environment."
echo "========================================================" 