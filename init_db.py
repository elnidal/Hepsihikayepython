from app import app, db, init_db

with app.app_context():
    db.create_all()
    init_db()
    print("Database initialized successfully!") 