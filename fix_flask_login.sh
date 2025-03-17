#!/bin/bash

# Script to push Flask-Login user_loader fix to GitHub

echo "===== Updating GitHub with Flask-Login fix ====="

# Add modified files
echo "Adding modified files..."
git add app.py

# Commit the changes
echo "Committing changes..."
git commit -m "Add user_loader callback function for Flask-Login"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should fix the Flask-Login error."
echo "Render should automatically redeploy your application." 