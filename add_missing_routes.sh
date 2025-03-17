#!/bin/bash

# Script to push missing routes fix to GitHub

echo "===== Updating GitHub with missing routes ====="

# Add modified files
echo "Adding modified files..."
git add app.py

# Commit the changes
echo "Committing changes..."
git commit -m "Add missing routes for category, post, author, and videos pages"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should add all the missing routes required by the templates."
echo "Render should automatically redeploy your application." 