# HepsiHikaye - Content Management Website

A modern content management website built with Flask for sharing stories, poems, articles, and news.

## Features

- Modern, responsive design
- Rich text editing with CKEditor
- Multiple content categories (Şiir, Öykü, Roman, Deneme, Makale, Haber)
- Image upload support
- Admin panel for content management
- Search functionality
- Category-based content organization

## Tech Stack

- Python 3.x
- Flask
- SQLAlchemy
- Flask-Admin
- Flask-Login
- CKEditor
- Bootstrap 5

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
