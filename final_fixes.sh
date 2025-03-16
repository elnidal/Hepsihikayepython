#!/bin/bash

echo "========================================================"
echo "  Pushing final fixes to GitHub for HepsiHikaye Website  "
echo "========================================================"
echo

echo "Adding fixes to Git..."
git add fix_all_issues.py final_fixes.sh

echo "Committing changes..."
git commit -m "Fix: Display all categories, delete test posts, fix admin panel

- Modified to show all categories regardless of post count
- Removed remaining test posts with 'persistence' keyword
- Fixed admin panel accessibility issues
- Added comprehensive logging for all operations"

echo "Pushing to GitHub..."
git push origin main

echo
echo "========================================================"
echo "All fixes pushed to GitHub!"
echo "The website will automatically deploy on Render.com"
echo "Your website should now show ALL categories and have a"
echo "functional admin panel at /admin"
echo "========================================================" 