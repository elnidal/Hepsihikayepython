#!/usr/bin/env python3
import os
import sys
import psycopg2
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

# Get database URL from environment with fallback to hardcoded value
database_url = os.environ.get('DATABASE_URL', '')

if not database_url:
    print("ERROR: DATABASE_URL environment variable is not set.")
    print("Please set DATABASE_URL to your database connection string.")
    sys.exit(1)

# Ensure URL uses postgresql:// scheme
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

def mask_password(url):
    """Mask the password in the URL for display"""
    parsed = urlparse(url)
    masked = f"{parsed.scheme}://{parsed.username}:****@{parsed.hostname}"
    if parsed.port:
        masked += f":{parsed.port}"
    masked += f"{parsed.path}"
    return masked

def test_connection():
    """Test connection to the database"""
    print(f"Testing connection to: {mask_password(database_url)}")
    
    # Parse the URL
    url = urlparse(database_url)
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port or 5432
    
    print(f"Connection parameters:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {dbname}")
    print(f"  User: {user}")
    
    try:
        # Try to connect with psycopg2
        print("\nTesting with psycopg2 (direct connection)...")
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            sslmode='require'
        )
        
        # Test a query
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            print(f"Query result: {result}")
        
        conn.close()
        print("✅ Direct connection successful!")
        
        # Try to connect with SQLAlchemy
        print("\nTesting with SQLAlchemy...")
        engine = create_engine(
            database_url,
            connect_args={"sslmode": "require"}
        )
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"Query result: {result.fetchone()}")
        
        print("✅ SQLAlchemy connection successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1) 