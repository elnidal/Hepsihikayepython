#!/bin/bash

# Script to push login route fixes to GitHub

echo "===== Updating GitHub with login route ====="

# Add modified files
echo "Adding modified files..."
git add app.py
git add templates/login.html

# Commit the changes
echo "Committing changes..."
git commit -m "Add login route and template for Flask-Login"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should add the login route required by Flask-Login."
echo "Render should automatically redeploy your application." 