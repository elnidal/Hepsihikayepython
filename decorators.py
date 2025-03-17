from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app, render_template, flash, redirect, url_for

def handle_db_error(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            flash('Veritabanı hatası oluştu. Lütfen daha sonra tekrar deneyiniz.', 'danger')
            return render_template('errors/500.html'), 500
    return decorated_function 