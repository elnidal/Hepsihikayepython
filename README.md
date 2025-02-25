# HepsiHikaye

A modern blog platform for sharing stories, poems, and literary content.

## Features

- Story, poem, and novel categories
- Image upload support with automatic optimization
- Rating system
- Admin panel for content management
- Mobile-friendly responsive design
- Modern UI with smooth transitions
- SEO-friendly URLs

## Technical Stack

- Python/Flask
- SQLite
- Flask-Admin
- Flask-Login
- CKEditor for rich text editing
- PIL for image processing
- Bootstrap for styling

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd story-website
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Create an admin user:
```python
flask shell
>>> from app import create_admin_user
>>> create_admin_user('admin', 'your-password')
>>> exit()
```

6. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:3000`

## Project Structure

- `app.py` - Main application file
- `templates/` - HTML templates
- `static/` - Static files (CSS, uploads)
- `instance/` - Instance-specific files
- `requirements.txt` - Python dependencies

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
