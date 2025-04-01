#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2
import sys
from app import app, db, Post, CATEGORIES

# Load environment variables
load_dotenv()

def check_db_connection():
    """Test connection to the PostgreSQL database specified in DATABASE_URL"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("Error: DATABASE_URL environment variable not set.")
        sys.exit(1)
    
    print(f"Attempting to connect to the database...")
    print(f"Connection string: {database_url.replace(':', '*****:', 1)}")
    
    try:
        # Parse connection string
        if database_url.startswith("postgresql://"):
            # Extract the components - this is a simple approach, may not handle all edge cases
            params = {}
            url = database_url.replace("postgresql://", "")
            
            # Split user:password@host:port/dbname
            userpass, hostportdb = url.split('@', 1)
            
            # Extract username and password
            if ':' in userpass:
                params['user'], params['password'] = userpass.split(':', 1)
            else:
                params['user'] = userpass
            
            # Extract host, port, and dbname
            if '/' in hostportdb:
                hostport, params['dbname'] = hostportdb.split('/', 1)
                if ':' in hostport:
                    params['host'], params['port'] = hostport.split(':', 1)
                else:
                    params['host'] = hostport
            else:
                params['host'] = hostportdb
        
            # Connect to the database
            conn = psycopg2.connect(**params)
            cur = conn.cursor()
            
            # Test the connection
            print("Connection successful!")
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print(f"PostgreSQL version: {version[0]}")
            
            # Check for existing tables
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cur.fetchall()
            
            if tables:
                print("\nExisting tables in the database:")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("\nNo tables found in the database.")
            
            # Close connection
            cur.close()
            conn.close()
            
        else:
            print("Error: DATABASE_URL must start with 'postgresql://'")
            sys.exit(1)
    
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    check_db_connection()

with app.app_context():
    # Check post count
    total_posts = Post.query.count()
    print(f"Total posts in database: {total_posts}")
    
    # Check categories setup
    print("\nCategories defined in app:")
    for slug, name in CATEGORIES:
        print(f" - {slug}: {name}")
    
    # Check posts in database
    print("\nSample posts:")
    posts = Post.query.limit(5).all()
    for post in posts:
        print(f" - ID: {post.id}, Title: {post.title}, Category: {post.category}")
    
    # Check category counts
    print("\nCategory counts:")
    for slug, name in CATEGORIES:
        count = Post.query.filter_by(category=slug).count()
        print(f" - {name}: {count} posts") 