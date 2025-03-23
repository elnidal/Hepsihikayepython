import os
import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migrations():
    """Run database migrations for PostgreSQL"""
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        return False
    
    # Try to connect to the database with retries
    conn = None
    retries = 5
    retry_delay = 3  # seconds
    
    for attempt in range(retries):
        try:
            logger.info(f"Connecting to database (attempt {attempt+1}/{retries})...")
            conn = psycopg2.connect(database_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            logger.info("Successfully connected to database")
            break
        except Exception as e:
            logger.error(f"Connection error (attempt {attempt+1}): {str(e)}")
            if attempt < retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Maximum retries reached. Could not connect to database.")
                return False
    
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if columns exist and add them if they don't
        logger.info("Checking for missing columns in post table...")
        add_column_if_not_exists(cursor, 'post', 'excerpt', 'TEXT')
        add_column_if_not_exists(cursor, 'post', 'published', 'BOOLEAN', 'TRUE')
        add_column_if_not_exists(cursor, 'post', 'featured', 'BOOLEAN', 'FALSE')
        add_column_if_not_exists(cursor, 'post', 'likes', 'INTEGER', '0')
        add_column_if_not_exists(cursor, 'post', 'dislikes', 'INTEGER', '0')
        
        logger.info("All migrations completed successfully")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Migration error: {str(e)}")
        if conn:
            conn.close()
        return False

def add_column_if_not_exists(cursor, table, column, data_type, default=None):
    """Add a column to a table if it doesn't exist"""
    try:
        # Check if column exists
        cursor.execute(
            sql.SQL("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s"),
            (table, column)
        )
        
        if cursor.fetchone() is None:
            # Column doesn't exist, add it
            query = sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                sql.Identifier(table),
                sql.Identifier(column),
                sql.SQL(data_type)
            )
            
            # Add default value if provided
            if default is not None:
                query = sql.SQL("{} DEFAULT {}").format(
                    query,
                    sql.SQL(default)
                )
            
            cursor.execute(query)
            logger.info(f"Added column '{column}' to table '{table}'")
        else:
            logger.info(f"Column '{column}' already exists in table '{table}'")
            
    except Exception as e:
        logger.error(f"Error adding column '{column}' to table '{table}': {str(e)}")
        raise

if __name__ == "__main__":
    if run_migrations():
        print("Migration completed successfully.")
    else:
        print("Migration failed. Check logs for details.") 