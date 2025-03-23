from app import db, app
from sqlalchemy import text
import sqlite3

def add_columns():
    """Add likes and dislikes columns to Post table"""
    with app.app_context():
        try:
            # For SQLite, we can use PRAGMA table_info
            conn = db.engine.connect()
            
            # Get column info for Post table
            result = conn.execute(text("PRAGMA table_info(post)"))
            columns = result.fetchall()
            
            # Check if columns exist
            column_names = [col[1] for col in columns]  # column name is at index 1
            likes_exists = 'likes' in column_names
            dislikes_exists = 'dislikes' in column_names
            
            # Add likes column if it doesn't exist
            if not likes_exists:
                conn.execute(text("ALTER TABLE post ADD COLUMN likes INTEGER DEFAULT 0"))
                print("Added 'likes' column to Post table")
            else:
                print("'likes' column already exists")
            
            # Add dislikes column if it doesn't exist
            if not dislikes_exists:
                conn.execute(text("ALTER TABLE post ADD COLUMN dislikes INTEGER DEFAULT 0"))
                print("Added 'dislikes' column to Post table")
            else:
                print("'dislikes' column already exists")
            
            # Commit the transaction
            db.session.commit()
            print("Migration completed successfully")
            
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    add_columns() 