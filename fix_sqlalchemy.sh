#!/bin/bash

# Script to push SQLAlchemy 2.0 compatibility fixes to GitHub

echo "===== Updating GitHub with SQLAlchemy 2.0 fixes ====="

# Add modified files
echo "Adding modified files..."
git add app.py
git add prod_debug.py

# Commit the changes
echo "Committing changes..."
git commit -m "Fix SQLAlchemy 2.0 compatibility issues"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should fix the 500 errors in production."
echo "Render should automatically redeploy your application." 