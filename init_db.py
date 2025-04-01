#!/usr/bin/env python3
import os
from app import app, db, User, Category, Post, migrate_from_json
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
            
        # Check if any categories exist
        if Category.query.count() == 0:
            # Create default categories
            categories = [
                Category(name='Öykü', slug='oyku'),
                Category(name='Roman', slug='roman'),
                Category(name='Şiir', slug='siir'),
                Category(name='Deneme', slug='deneme'),
                Category(name='İnceleme', slug='inceleme'),
                Category(name='Haber', slug='haber'),
                Category(name='Video', slug='video')
            ]
            db.session.add_all(categories)
            db.session.commit()
            print("Default categories created successfully")
            
        # Check if any posts exist
        if Post.query.count() == 0:
            # Try to migrate from JSON files if they exist
            try:
                migrate_from_json()
                print("Migration from JSON completed")
            except Exception as e:
                print(f"Migration error: {str(e)}")
                
                # Create a welcome post if migration failed
                welcome_post = Post(
                    title='Hoş Geldiniz',
                    content='Hepsi Hikaye web sitesine hoş geldiniz. Bu bir örnek içeriktir.',
                    category_id=1,  # Öykü
                    published=True,
                    featured=True
                )
                db.session.add(welcome_post)
                db.session.commit()
                print("Welcome post created successfully")

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