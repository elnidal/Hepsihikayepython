#!/bin/bash

# Script to push our improved fixes for categories and static files to GitHub

echo "===== Updating GitHub with comprehensive fixes for categories and templates ====="

# Add modified files
echo "Adding modified files..."
git add app.py
git add diagnostics.py
git add fix_category_display.sh

# Commit the changes
echo "Committing changes..."
git commit -m "Fix categories display, improve error handling, and add diagnostics"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes include:"
echo "1. Improved context processor for categories with comprehensive error handling"
echo "2. Fixed upload URL handling to ensure static files load correctly"
echo "3. Added diagnostic tools to troubleshoot template and static file issues"
echo "4. Fixed upload directory path handling to prevent formatting errors"
echo 
echo "Render should automatically redeploy your application with these fixes." 