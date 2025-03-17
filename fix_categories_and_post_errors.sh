#!/bin/bash

# Script to push category display and post error fixes to GitHub

echo "===== Updating GitHub with category display and post error fixes ====="

# Add modified files
echo "Adding modified files..."
git add app.py
git add check_db.py

# Commit the changes
echo "Committing changes..."
git commit -m "Fix categories display and post error handling with context processor"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should fix the missing categories and post errors."
echo "Render should automatically redeploy your application." 