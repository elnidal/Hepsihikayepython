#!/bin/bash

echo "=== Updating HepsiHikaye Website ==="
echo "Pushing fixes to GitHub for automatic deployment to Render.com"

# Add the new files to Git
git add check_categories.py fix_website.py update_site.sh

# Commit the changes
git commit -m "Fix: Updated categories and removed test post

- Added scripts to verify and fix categories
- Removed test post with ID 1
- Ensured all posts have valid categories
- Fixed website for production"

# Push to GitHub
git push origin main

echo ""
echo "=== Update Complete ==="
echo "Changes have been pushed to GitHub and will automatically deploy to Render.com"
echo "Your website should now be fully functional with all categories displaying correctly!"
echo "===========================================" 