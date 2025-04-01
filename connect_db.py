#!/usr/bin/env python3
import psycopg2

# Connection parameters directly
DB_HOST = "db.uimiziayidrctdaqqvyg.supabase.co"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "547965"

print(f"Attempting to connect to PostgreSQL database at {DB_HOST}...")

try:
    # Connect directly using parameters
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    # Create a cursor
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
    
    # Close cursor and connection
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Connection failed: {str(e)}") 