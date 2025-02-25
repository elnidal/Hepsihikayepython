# Content Management Website

This is a simple content management website built with Flask that allows you to:
- Create categories for your content
- Add posts with text and images
- Embed YouTube videos
- Manage everything through an easy-to-use admin interface

## Setup

1. Make sure you have Python installed on your computer

2. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the requirements:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Access the website:
- Main website: http://localhost:5000
- Admin panel: http://localhost:5000/admin

## Using the Admin Panel

1. Categories:
   - Go to "Category" in the admin panel
   - Click "Create" to add a new category
   - Fill in the name (the slug will be generated automatically)

2. Posts:
   - Go to "Post" in the admin panel
   - Click "Create" to add a new post
   - Fill in the title and content
   - Upload an image if desired
   - Select the category for the post

3. Videos:
   - Go to "Video" in the admin panel
   - Click "Create" to add a new video
   - Add the title
   - For YouTube videos, get the embed code from YouTube (Share > Embed) and paste it in the "YouTube Embed" field

## File Structure

- `app.py`: Main application file
- `templates/`: HTML templates
  - `base.html`: Base template with common elements
  - `index.html`: Home page template
  - `category.html`: Category page template
  - `videos.html`: Videos page template
- `static/`: Static files (CSS, uploaded images)
- `site.db`: SQLite database (created automatically)

## Customization

You can customize the look and feel of your website by:
1. Modifying the templates in the `templates` folder
2. Editing the CSS in `static/style.css`
3. Adding new routes in `app.py`
