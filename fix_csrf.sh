#!/bin/bash

# Script to push CSRF token fixes to GitHub

echo "Pushing fixes for CSRF token issues in templates..."
echo "====================================================="

# Add modified files
git add app.py templates/base.html templates/post_detail.html fix_csrf.sh

# Commit changes
git commit -m "Fix: Made CSRF token handling robust to prevent 500 errors on post pages

- Added conditional checks in templates to verify request context is available
- Added related posts to post detail page
- Improved error handling around CSRF functions"

# Push changes to the main branch
git push origin main

echo "====================================================="
echo "Changes pushed to GitHub! The application should redeploy with these fixes."
echo "The fixed CSRF token handling should resolve 500 errors on post pages." 