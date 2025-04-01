#!/usr/bin/env python3
import psycopg2

# Supabase connection string parts
DB_HOST = "db.uimiziayidrctdaqqvyg.supabase.co"
DB_PORT = "5432"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "547965"

print(f"Attempting to create tables in database...")

# SQL to create tables
CREATE_TABLES_SQL = """
-- User table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(250) NOT NULL
);

-- Category table
CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL
);

-- Post table
CREATE TABLE IF NOT EXISTS post (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    image VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    published BOOLEAN DEFAULT TRUE,
    featured BOOLEAN DEFAULT FALSE,
    category_id INTEGER REFERENCES category(id)
);

-- Video table
CREATE TABLE IF NOT EXISTS video (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    url VARCHAR(255) NOT NULL,
    thumbnail_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    views INTEGER DEFAULT 0,
    published BOOLEAN DEFAULT TRUE,
    category_id INTEGER REFERENCES category(id)
);

-- Comment table
CREATE TABLE IF NOT EXISTS comment (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    post_id INTEGER REFERENCES post(id) ON DELETE CASCADE,
    video_id INTEGER REFERENCES video(id) ON DELETE CASCADE,
    CHECK (post_id IS NOT NULL OR video_id IS NOT NULL)
);

-- Insert default admin user (password is 'admin')
INSERT INTO "user" (username, password) 
VALUES ('admin', 'pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f')
ON CONFLICT (username) DO NOTHING;

-- Insert default categories
INSERT INTO category (name, slug) VALUES 
    ('Öykü', 'oyku'),
    ('Roman', 'roman'),
    ('Şiir', 'siir'),
    ('Deneme', 'deneme'),
    ('İnceleme', 'inceleme'),
    ('Haber', 'haber'),
    ('Video', 'video')
ON CONFLICT (slug) DO NOTHING;

-- Insert a welcome post
INSERT INTO post (title, content, category_id, published, featured)
SELECT 'Hoş Geldiniz', 'Hepsi Hikaye web sitesine hoş geldiniz. Bu bir örnek içeriktir.', id, TRUE, TRUE
FROM category WHERE slug = 'oyku'
LIMIT 1;
"""

try:
    # Connect to the database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    # Set autocommit to True so each command runs immediately
    conn.autocommit = True
    
    # Create a cursor
    cur = conn.cursor()
    
    # Execute the SQL commands
    cur.execute(CREATE_TABLES_SQL)
    
    print("Tables created successfully!")
    
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
            
        # Check the user table
        cur.execute("SELECT id, username FROM \"user\"")
        users = cur.fetchall()
        print("\nUsers in the database:")
        for user in users:
            print(f"  - ID: {user[0]}, Username: {user[1]}")
            
        # Check the category table
        cur.execute("SELECT id, name, slug FROM category")
        categories = cur.fetchall()
        print("\nCategories in the database:")
        for category in categories:
            print(f"  - ID: {category[0]}, Name: {category[1]}, Slug: {category[2]}")
            
        # Check the post table
        cur.execute("SELECT id, title FROM post")
        posts = cur.fetchall()
        print("\nPosts in the database:")
        for post in posts:
            print(f"  - ID: {post[0]}, Title: {post[1]}")
    else:
        print("\nNo tables found in the database.")
    
    # Close cursor and connection
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Operation failed: {str(e)}") 