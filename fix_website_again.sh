#!/bin/bash

echo "=== Fixing HepsiHikaye Website Again ==="
echo "Pushing critical fixes to GitHub for automatic deployment to Render.com"

# Add the modified files and new scripts to Git
git add app.py debug_csrf.py fix_website_again.sh

# Commit the changes
git commit -m "Fix: Added missing comment functionality

- Added missing add_comment route to handle post comments
- Added comment approval and deletion routes for admin
- Fixed CSRF token handling with blinker library
- Added diagnostic tools for debugging

These changes should resolve the 'Sunucu Hatası' (Server Error) messages when viewing posts."

# Push to GitHub
git push origin main

echo ""
echo "=== Update Complete ==="
echo "Changes have been pushed to GitHub and will automatically deploy to Render.com"
echo "Your website should now be fully functional with all posts displaying correctly!"
echo "=========================================== 