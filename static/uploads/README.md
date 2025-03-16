# Uploads Directory

This directory is used for storing uploaded files for the HepsiHikaye website.

## Important Note

When deploying to Render.com:
1. This directory is included in the Git repository to ensure it exists in the deployment.
2. Any files uploaded in production will NOT persist between deployments because Render uses an ephemeral filesystem.
3. For production use, consider using a cloud storage service like AWS S3.

## Default Images

Place default images in this directory to ensure they're available in production.
