import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check environment variables and configuration"""
    logger.info("==== PRODUCTION ENVIRONMENT DIAGNOSTIC ====")
    
    # Check environment
    flask_env = os.environ.get("FLASK_ENV", "Not set")
    logger.info(f"FLASK_ENV: {flask_env}")
    
    # Check if we're in production
    is_production = flask_env == "production"
    logger.info(f"Running in production mode: {is_production}")
    
    # Check upload directories
    static_folder = os.path.join(os.getcwd(), 'static')
    static_uploads = os.path.join(static_folder, 'uploads')
    prod_uploads = '/opt/render/project/src/uploads'
    
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Static folder exists: {os.path.exists(static_folder)}")
    logger.info(f"Static uploads exists: {os.path.exists(static_uploads)}")
    logger.info(f"Production uploads exists: {os.path.exists(prod_uploads)}")
    
    # List files in the current directory
    logger.info("Files in current directory:")
    for f in os.listdir('.'):
        logger.info(f"  - {f}")

def check_database():
    """Check database connection"""
    logger.info("==== DATABASE CONNECTION DIAGNOSTIC ====")
    
    # Get database URL from environment variables with fallback
    database_url = os.environ.get('DATABASE_URL', 
        "postgresql://hepsihikaye_wyg3_user:JWWumjYdrR15YATOT4KJvsRz4XxkRxzX@dpg-cvanpdlumphs73ag0b80-a.oregon-postgres.render.com/hepsihikaye_wyg3")
    
    # If the URL starts with 'postgres://', convert it to 'postgresql://'
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Don't log the actual credentials
    masked_url = database_url.replace(database_url.split('@')[0], 'postgresql://****:****')
    logger.info(f"Database URL: {masked_url}")
    
    try:
        # Create engine with SSL required
        engine = create_engine(
            database_url, 
            connect_args={'sslmode': 'require'}
        )
        
        # Test connection
        connection = engine.connect()
        logger.info("Database connection successful!")
        
        # Test a simple query
        result = connection.execute("SELECT 1")
        logger.info(f"Query result: {result.fetchone()}")
        
        # Close connection
        connection.close()
        logger.info("Database connection closed")
        
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

def check_imports():
    """Check critical imports"""
    logger.info("==== IMPORT DIAGNOSTIC ====")
    
    try:
        import flask
        logger.info(f"Flask version: {flask.__version__}")
    except ImportError:
        logger.error("Flask not installed")
    
    try:
        import psycopg2
        logger.info(f"psycopg2 version: {psycopg2.__version__}")
    except ImportError:
        logger.error("psycopg2 not installed")
    
    try:
        import sqlalchemy
        logger.info(f"SQLAlchemy version: {sqlalchemy.__version__}")
    except ImportError:
        logger.error("SQLAlchemy not installed")
    
    try:
        from flask_sqlalchemy import SQLAlchemy
        logger.info("Flask-SQLAlchemy installed")
    except ImportError:
        logger.error("Flask-SQLAlchemy not installed")
    
    try:
        from PIL import Image
        logger.info(f"Pillow installed")
    except ImportError:
        logger.error("Pillow not installed")
        
def run_diagnostics():
    """Run all diagnostic checks"""
    try:
        check_environment()
        check_imports()
        check_database()
        logger.info("==== DIAGNOSTICS COMPLETE ====")
    except Exception as e:
        logger.error(f"Diagnostic error: {str(e)}")

if __name__ == "__main__":
    run_diagnostics() 