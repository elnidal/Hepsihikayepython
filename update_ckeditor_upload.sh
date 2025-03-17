#!/bin/bash

# Script to push CKEditor upload route fixes to GitHub

echo "===== Updating GitHub with CKEditor upload route fixes ====="

# Add modified/new files
echo "Adding modified files..."
git add app.py
git add templates/admin/media_library.html

# Commit the changes
echo "Committing changes..."
git commit -m "Add missing upload route and media library for CKEditor integration"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should fix the CKEditor upload functionality."
echo "Render should automatically redeploy your application." 