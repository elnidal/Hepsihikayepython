#!/usr/bin/env python3
import os
from app import app, db, User
from werkzeug.security import generate_password_hash

def init_db():
    """Initialize the database with required tables and default admin user."""
    # Create all tables based on models
    with app.app_context():
        # Create tables
        db.create_all()
        
        print("Tables created successfully.")
        
        # Check if admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            # Create admin user
            admin_user = User(username='admin', password=generate_password_hash('admin'))
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created successfully")
        else:
            print("Admin user already exists")

if __name__ == "__main__":
    # Print the database URL (with password masked)
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    if 'postgresql://' in db_url:
        masked_url = db_url.replace(db_url.split('@')[0].split('://')[1].split(':')[1], '*****')
        print(f"Using database: {masked_url}")
    
    try:
        init_db()
        print("Database initialization completed successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise 