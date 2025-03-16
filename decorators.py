from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

def handle_db_error(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in {f.__name__}: {str(e)}")
            return None
    return decorated_function 