import os
import subprocess
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)

def backup_database():
    """Create a backup of the PostgreSQL database"""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logging.error("DATABASE_URL not found in environment variables")
            return False
            
        # Parse database URL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Create backup directory if it doesn't exist
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'hepsihikaye_backup_{timestamp}.sql')
        
        # Extract connection details from DATABASE_URL
        from urllib.parse import urlparse
        url = urlparse(database_url)
        
        # Set PostgreSQL environment variables
        env = os.environ.copy()
        env['PGHOST'] = url.hostname
        env['PGPORT'] = str(url.port or 5432)
        env['PGUSER'] = url.username
        env['PGPASSWORD'] = url.password
        env['PGDATABASE'] = url.path[1:]  # Remove leading slash
        
        # Run pg_dump
        cmd = ['pg_dump', '--clean', '--if-exists', '--format=p', '--file=' + backup_file]
        
        subprocess.run(cmd, env=env, check=True)
        
        logging.info(f"Database backup created successfully: {backup_file}")
        return True
        
    except Exception as e:
        logging.error(f"Backup failed: {str(e)}")
        return False

if __name__ == '__main__':
    backup_database() 