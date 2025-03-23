from app import app, db, User, Category, Post, Video, generate_password_hash
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_local_db():
    try:
        with app.app_context():
            # Drop all tables
            db.drop_all()
            logger.info("Dropped all existing tables")

            # Create all tables
            db.create_all()
            logger.info("Created all tables")

            # Create default admin user
            admin = User(
                username='admin',
                password=generate_password_hash('admin')
            )
            db.session.add(admin)
            
            # Create default categories
            default_categories = [
                {'name': 'Öykü', 'slug': 'oyku'},
                {'name': 'Roman', 'slug': 'roman'},
                {'name': 'Şiir', 'slug': 'siir'},
                {'name': 'Deneme', 'slug': 'deneme'},
                {'name': 'İnceleme', 'slug': 'inceleme'},
                {'name': 'Haber', 'slug': 'haber'},
                {'name': 'Video', 'slug': 'video'}
            ]

            created_categories = []
            for cat_data in default_categories:
                category = Category(name=cat_data['name'], slug=cat_data['slug'])
                db.session.add(category)
                created_categories.append(category)
            
            # Commit changes
            db.session.commit()
            logger.info("Created default admin user and categories")
            
            # Create sample post for each category
            for category in created_categories:
                sample_post = Post(
                    title=f"Sample {category.name} Post",
                    content=f"This is a sample post in the {category.name} category.",
                    category_id=category.id
                )
                db.session.add(sample_post)
            
            # Create a sample video
            sample_video = Video(
                title="Sample Video",
                youtube_id="dQw4w9WgXcQ",  # Rick Roll as sample video
                description="This is a sample video."
            )
            db.session.add(sample_video)
            
            # Commit all changes
            db.session.commit()
            logger.info("Created sample content")
            
            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join(app.static_folder, 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
                logger.info("Created uploads directory")
            
            return True
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()
        return False

if __name__ == '__main__':
    success = init_local_db()
    if success:
        logger.info("Database initialized successfully")
    else:
        logger.error("Database initialization failed") 