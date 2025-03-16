import os
import sys
import logging
from app import app, db, Post
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_post_content(post_id=None):
    """Check post content for potential problematic elements"""
    with app.app_context():
        if post_id:
            posts = Post.query.filter_by(id=post_id).all()
        else:
            posts = Post.query.all()
        
        logger.info(f"Checking {len(posts)} posts for potential issues...")
        
        for post in posts:
            logger.info(f"Post ID: {post.id}, Title: {post.title}")
            
            # Check for iframes
            if "<iframe" in post.content.lower():
                logger.warning(f"Post {post.id} contains iframe elements")
                iframe_count = post.content.lower().count("<iframe")
                logger.warning(f"  - Found {iframe_count} iframe elements")
                
                # Extract iframe src attributes
                iframe_srcs = re.findall(r'<iframe.*?src=["\'](.*?)["\']', post.content, re.IGNORECASE)
                for src in iframe_srcs:
                    logger.warning(f"  - iframe src: {src}")
            
            # Check for bots or chatbots
            if "bot" in post.content.lower():
                logger.warning(f"Post {post.id} contains 'bot' in content")
                
                # Look for bot-related elements
                bot_elements = re.findall(r'<[^>]*bot[^>]*>', post.content, re.IGNORECASE)
                for element in bot_elements:
                    logger.warning(f"  - Bot element: {element}")
            
            # Check for script tags
            if "<script" in post.content.lower():
                logger.warning(f"Post {post.id} contains script elements")
                script_count = post.content.lower().count("<script")
                logger.warning(f"  - Found {script_count} script elements")
                
                # Extract script sources
                script_srcs = re.findall(r'<script.*?src=["\'](.*?)["\']', post.content, re.IGNORECASE)
                for src in script_srcs:
                    logger.warning(f"  - script src: {src}")
            
            # Check for excessive size
            if len(post.content) > 50000:
                logger.warning(f"Post {post.id} has very large content: {len(post.content)} characters")
            
            # Check for unclosed HTML tags
            unclosed_tags = re.findall(r'<([a-z]+)[^>]*>[^<]*(?=<(?!\1))', post.content, re.IGNORECASE)
            if unclosed_tags:
                logger.warning(f"Post {post.id} might have unclosed HTML tags: {unclosed_tags}")

def fix_post_content(post_id):
    """Fix problematic content in a post"""
    with app.app_context():
        post = Post.query.get(post_id)
        if not post:
            logger.error(f"Post {post_id} not found")
            return False
        
        logger.info(f"Fixing content for post {post_id}: {post.title}")
        
        # Store original content for reference
        original_content = post.content
        
        # Replace problematic iframe elements with a safe placeholder
        if "<iframe" in post.content.lower():
            logger.info("Replacing iframe elements...")
            post.content = re.sub(
                r'<iframe.*?src=["\'](.*?)["\'].*?</iframe>',
                r'<div class="iframe-placeholder" data-src="\1">[Embedded content not displayed for security reasons]</div>',
                post.content, 
                flags=re.IGNORECASE
            )
        
        # Replace script tags
        if "<script" in post.content.lower():
            logger.info("Removing script elements...")
            post.content = re.sub(
                r'<script.*?>.*?</script>',
                '',
                post.content, 
                flags=re.DOTALL | re.IGNORECASE
            )
        
        # Close unclosed tags
        # This is a simplified version - a full parser would be better
        for tag in ['div', 'span', 'p', 'a', 'b', 'i', 'strong', 'em']:
            open_count = post.content.lower().count(f"<{tag}")
            close_count = post.content.lower().count(f"</{tag}")
            if open_count > close_count:
                logger.info(f"Adding missing closing tags for <{tag}>...")
                post.content += f"</{tag}>" * (open_count - close_count)
        
        # Remove potentially problematic bot elements
        if "bot" in post.content.lower():
            logger.info("Fixing bot-related elements...")
            post.content = re.sub(
                r'<[^>]*chatbot[^>]*>.*?</[^>]*chatbot[^>]*>',
                '<div>[Chatbot element removed]</div>',
                post.content,
                flags=re.DOTALL | re.IGNORECASE
            )
        
        # Check if content changed
        if post.content != original_content:
            logger.info("Content was modified, saving changes...")
            db.session.commit()
            return True
        else:
            logger.info("No changes were needed")
            return False

def main():
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "check" and len(sys.argv) > 2:
            post_id = int(sys.argv[2])
            logger.info(f"Checking post with ID: {post_id}")
            check_post_content(post_id)
        elif action == "check-all":
            logger.info("Checking all posts")
            check_post_content()
        elif action == "fix" and len(sys.argv) > 2:
            post_id = int(sys.argv[2])
            logger.info(f"Fixing post with ID: {post_id}")
            fix_post_content(post_id)
        else:
            logger.error("Invalid arguments")
            print("Usage: python check_post_content.py [check|check-all|fix] [post_id]")
    else:
        logger.info("Checking all posts by default")
        check_post_content()

if __name__ == "__main__":
    main() 