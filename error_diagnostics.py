import os
import sys
import logging
from flask import Flask
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_database_connection():
    """Test the database connection"""
    try:
        # Get database URL from environment variables with fallback
        database_url = os.environ.get('DATABASE_URL', "postgresql://hepsihikaye_wyg3_user:JWWumjYdrR15YATOT4KJvsRz4XxkRxzX@dpg-cvanpdlumphs73ag0b80-a.oregon-postgres.render.com/hepsihikaye_wyg3")
        
        # If the URL starts with 'postgres://', convert it to 'postgresql://'
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        logger.info(f"Testing connection to database: {database_url}")
        
        # Create a SQLAlchemy engine
        engine = create_engine(database_url)
        
        # Test the connection
        with engine.connect() as connection:
            logger.info("Successfully connected to the database")
            
            # Test a simple query
            result = connection.execute(text("SELECT 1"))
            logger.info("Successfully executed a test query")
            
            # Test a more complex query to verify table access
            try:
                # Check if User table exists and is accessible
                result = connection.execute(text("SELECT COUNT(*) FROM \"user\""))
                user_count = result.scalar()
                logger.info(f"User table exists and contains {user_count} records")
                
                # Check if Post table exists and is accessible
                result = connection.execute(text("SELECT COUNT(*) FROM post"))
                post_count = result.scalar()
                logger.info(f"Post table exists and contains {post_count} records")
                
                # Check additional tables
                table_names = ['rating', 'setting', 'video']
                for table in table_names:
                    try:
                        result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        logger.info(f"{table.capitalize()} table exists and contains {count} records")
                    except Exception as e:
                        logger.error(f"Error accessing {table} table: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error verifying tables: {str(e)}")
        
        return True
    except OperationalError as e:
        logger.error(f"Database connection error: {str(e)}")
        return False
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

def check_template_errors():
    """Check for common template rendering errors"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    logger.info(f"Checking templates in {template_dir}")
    
    if not os.path.exists(template_dir):
        logger.error(f"Template directory does not exist: {template_dir}")
        return False
    
    # Check critical templates
    critical_templates = ['base.html', 'index.html', 'category.html', 'post_detail.html', 'login.html']
    for template in critical_templates:
        template_path = os.path.join(template_dir, template)
        if not os.path.exists(template_path):
            logger.error(f"Critical template missing: {template}")
            return False
        logger.info(f"Template exists: {template}")
    
    # Additional checks for url_for references in templates could be added here
    
    return True

def check_configuration():
    """Check for common configuration issues"""
    # Check SECRET_KEY
    if not os.environ.get('SECRET_KEY'):
        logger.warning("SECRET_KEY environment variable is not set, using default")
    
    # Check upload directory
    upload_dir = os.path.join(os.path.dirname(__file__), 'static/uploads')
    if not os.path.exists(upload_dir):
        logger.warning(f"Upload directory does not exist: {upload_dir}")
        try:
            os.makedirs(upload_dir, exist_ok=True)
            logger.info(f"Created upload directory: {upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create upload directory: {str(e)}")
    else:
        logger.info(f"Upload directory exists: {upload_dir}")
    
    # Check database URL
    if not os.environ.get('DATABASE_URL'):
        logger.warning("DATABASE_URL environment variable is not set, using default")
    
    return True

def main():
    """Run diagnostic checks"""
    logger.info("Starting diagnostics for HepsiHikaye application")
    
    # Check configuration
    logger.info("\n--- Checking configuration ---")
    check_configuration()
    
    # Check database connection
    logger.info("\n--- Checking database connection ---")
    check_database_connection()
    
    # Check templates
    logger.info("\n--- Checking templates ---")
    check_template_errors()
    
    logger.info("\nDiagnostics completed. Check logs above for any errors or warnings.")

if __name__ == "__main__":
    main() 