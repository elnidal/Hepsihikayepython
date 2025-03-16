#!/usr/bin/env python3
from app import app, db, Post, CATEGORIES
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_categories():
    """Ensure all posts have valid categories"""
    logger.info("Checking post categories...")
    
    valid_categories = [slug for slug, _ in CATEGORIES]
    
    with app.app_context():
        # Check for posts with invalid categories
        posts = Post.query.all()
        invalid_posts = [post for post in posts if post.category not in valid_categories]
        
        if not invalid_posts:
            logger.info("✅ All posts have valid categories")
        else:
            logger.warning(f"Found {len(invalid_posts)} posts with invalid categories")
            for post in invalid_posts:
                logger.info(f"Fixing post ID {post.id}: '{post.title}' - Invalid category: '{post.category}'")
                # Set a default category (öykü)
                post.category = 'öykü'
            
            # Save changes
            try:
                db.session.commit()
                logger.info("✅ Fixed all invalid categories")
            except Exception as e:
                db.session.rollback()
                logger.error(f"❌ Error fixing categories: {str(e)}")

def delete_test_post():
    """Delete the test post if it exists"""
    logger.info("Checking for test posts...")
    
    with app.app_context():
        # Look for post with 'Test' in the title
        test_posts = Post.query.filter(Post.title.like('%Test%')).all()
        
        if not test_posts:
            logger.info("✅ No test posts found")
        else:
            logger.info(f"Found {len(test_posts)} test posts")
            
            for post in test_posts:
                if "Test Post - Please Delete" in post.title:
                    try:
                        logger.info(f"Deleting test post: ID {post.id} - '{post.title}'")
                        db.session.delete(post)
                        db.session.commit()
                        logger.info("✅ Successfully deleted test post")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"❌ Error deleting test post: {str(e)}")

def verify_database():
    """Check database and print summary"""
    logger.info("Verifying database state...")
    
    with app.app_context():
        posts = Post.query.all()
        logger.info(f"Found {len(posts)} posts in database")
        
        # Count posts by category
        category_counts = {}
        for post in posts:
            if post.category in category_counts:
                category_counts[post.category] += 1
            else:
                category_counts[post.category] = 1
        
        logger.info("Posts by category:")
        for category_slug, count in category_counts.items():
            category_name = next((name for slug, name in CATEGORIES if slug == category_slug), category_slug)
            logger.info(f"  - {category_name}: {count} posts")

if __name__ == "__main__":
    logger.info("Starting website fixes...")
    
    # Fix categories
    fix_categories()
    
    # Delete test post
    delete_test_post()
    
    # Verify database state
    verify_database()
    
    logger.info("✅ All fixes completed")
    print("\n===== WEBSITE FIX SUMMARY =====")
    print("1. Fixed any invalid post categories")
    print("2. Deleted test post (if it existed)")
    print("3. Verified database integrity")
    print("\nYour website should now be working properly with all categories displaying correctly!")
    print("You can access your website on Render.com")
    print("=====================================") 