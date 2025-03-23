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
        
        # First check if the post table exists
        cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'post')"
        )
        if not cursor.fetchone()[0]:
            logger.error("Post table does not exist. Database may not be initialized properly.")
            return False
        
        # List all required columns with their types and defaults
        columns = [
            ('id', 'SERIAL PRIMARY KEY', None),  # This should already exist
            ('title', 'VARCHAR(200) NOT NULL', None),  # This should already exist
            ('content', 'TEXT NOT NULL', None),  # This should already exist
            ('excerpt', 'TEXT', None),
            ('image', 'VARCHAR(200)', None),  # Missing column found in logs
            ('views', 'INTEGER', '0'),
            ('likes', 'INTEGER', '0'),
            ('dislikes', 'INTEGER', '0'),
            ('published', 'BOOLEAN', 'TRUE'),
            ('featured', 'BOOLEAN', 'FALSE'),
            ('category_id', 'INTEGER', None),  # This should already exist
            ('created_at', 'TIMESTAMP', 'CURRENT_TIMESTAMP'),  # This should already exist
            ('updated_at', 'TIMESTAMP', 'CURRENT_TIMESTAMP')  # This should already exist
        ]
        
        # Check each column and add if it doesn't exist
        logger.info("Checking for missing columns in post table...")
        for column_name, data_type, default in columns:
            add_column_if_not_exists(cursor, 'post', column_name, data_type, default)
        
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
        # Skip id column as it's the primary key and should already exist
        if column == 'id':
            return
            
        # Check if column exists
        cursor.execute(
            sql.SQL("SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s"),
            (table, column)
        )
        
        if cursor.fetchone() is None:
            # Column doesn't exist, add it
            if default is not None:
                query = sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} {} DEFAULT {}").format(
                    sql.Identifier(table),
                    sql.Identifier(column),
                    sql.SQL(data_type),
                    sql.SQL(default)
                )
            else:
                query = sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} {}").format(
                    sql.Identifier(table),
                    sql.Identifier(column),
                    sql.SQL(data_type)
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