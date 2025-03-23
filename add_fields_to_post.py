import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_fields_to_post_table():
    db_path = 'hepsihikaye.db'
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(post)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Add excerpt column if it doesn't exist
        if 'excerpt' not in column_names:
            logger.info("Adding 'excerpt' column to Post table")
            cursor.execute("ALTER TABLE post ADD COLUMN excerpt TEXT")
        else:
            logger.info("'excerpt' column already exists in Post table")
        
        # Add published column if it doesn't exist
        if 'published' not in column_names:
            logger.info("Adding 'published' column to Post table")
            cursor.execute("ALTER TABLE post ADD COLUMN published BOOLEAN DEFAULT 1")
        else:
            logger.info("'published' column already exists in Post table")
        
        # Add featured column if it doesn't exist
        if 'featured' not in column_names:
            logger.info("Adding 'featured' column to Post table")
            cursor.execute("ALTER TABLE post ADD COLUMN featured BOOLEAN DEFAULT 0")
        else:
            logger.info("'featured' column already exists in Post table")
        
        conn.commit()
        logger.info("Post table migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if add_fields_to_post_table():
        print("Migration completed successfully.")
    else:
        print("Migration failed. Check logs for details.") 