# HepsiHikaye

A modern blog platform for sharing stories, poems, and literary content.

## Features

- Story, poem, and novel categories
- Image upload support with automatic optimization
- Rating system with likes and dislikes
- Admin panel for content management
- Mobile-friendly responsive design
- Modern UI with smooth transitions
- SEO-friendly URLs
- YouTube video integration

## Technical Stack

- Python 3/Flask
- SQLite
- Flask-Admin
- Flask-Login
- CKEditor for rich text editing
- PIL for image processing
- Bootstrap for styling

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/elnidal/Hepsihikayepython.git
cd Hepsihikayepython
```

2. Create and activate virtual environment:

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
# For macOS/Linux
python3 app.py

# For Windows
python app.py
```

The application will be available at `http://127.0.0.1:5000`

### Admin Access

The default admin credentials are:
- Username: admin
- Password: (set during first run)

If you need to reset the admin password, you can do so by:
```bash
# For macOS/Linux
python3 -c "from app import db, User; user = User.query.filter_by(username='admin').first(); user.password = 'new-password-hash'; db.session.commit()"

# For Windows
python -c "from app import db, User; user = User.query.filter_by(username='admin').first(); user.password = 'new-password-hash'; db.session.commit()"
```

## Project Structure

- `app.py` - Main application file
- `templates/` - HTML templates
- `static/` - Static files (CSS, JS, images)
- `instance/` - Instance-specific files (database)
- `requirements.txt` - Python dependencies

## Deployment

The application is configured for deployment on Render.com using the `render.yaml` file.

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'flask'**
   - Make sure you've activated your virtual environment and installed all requirements

2. **Command not found: python**
   - On macOS/Linux, use `python3` instead of `python`

3. **Database errors**
   - Check that the SQLite database file exists and has proper permissions

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
