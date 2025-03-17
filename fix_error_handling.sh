#!/bin/bash

# Script to push error handling fixes to GitHub

echo "===== Updating GitHub with enhanced error handling ====="

# Add modified/new files
echo "Adding modified files..."
git add app.py
git add templates/errors/500.html
git add templates/errors/404.html
git add templates/errors/db_error.html
git add error_diagnostics.py
git add debug_server.py

# Commit the changes
echo "Committing changes..."
git commit -m "Add enhanced error handling and diagnostics tools"

# Push to main branch
echo "Pushing to GitHub..."
git push origin main

echo "===== GitHub update complete ====="
echo "These changes should improve error handling and diagnostics."
echo "Render should automatically redeploy your application." 