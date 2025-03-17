#!/bin/bash

# Script to push index route fix to GitHub

echo "===== Updating GitHub with index route ====="

# Add modified files
echo "Adding modified files..."
git add app.py

# Commit the changes
echo "Committing changes..."
git commit -m "Add root (/) route to fix 404 error on homepage"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should fix the 404 error when accessing the homepage."
echo "Render should automatically redeploy your application." 