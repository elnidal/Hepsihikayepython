import os
import sys
import logging
from app import app, db, Post
import re
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_post_content(post_id):
    """Retrieve and display the content of a specific post"""
    with app.app_context():
        post = Post.query.get(post_id)
        if not post:
            logger.error(f"Post with ID {post_id} not found")
            return
        
        logger.info(f"Post {post_id}: {post.title}")
        logger.info(f"Content length: {len(post.content)} characters")
        logger.info(f"Content preview: {post.content[:100]}...")
        
        return post.content

def fix_all_posts():
    """Fix HTML issues in all posts"""
    with app.app_context():
        posts = Post.query.all()
        logger.info(f"Found {len(posts)} posts to process")
        
        fixed_count = 0
        for post in posts:
            if fix_post_html(post.id):
                fixed_count += 1
        
        logger.info(f"Fixed {fixed_count} posts out of {len(posts)}")
        return fixed_count

def fix_post_html(post_id):
    """Fix HTML issues in a specific post"""
    with app.app_context():
        post = Post.query.get(post_id)
        if not post:
            logger.error(f"Post with ID {post_id} not found")
            return False
        
        logger.info(f"Processing post {post_id}: {post.title}")
        
        # Store original content for comparison
        original_content = post.content
        
        # Handle special cases before running through BeautifulSoup
        
        # Fix bot iframe code if present
        if "bot" in post.content.lower() or "chatbot" in post.content.lower():
            logger.info(f"Post {post_id} may have bot-related content")
            
            # Check for common bot iframe patterns
            bot_iframes = re.findall(r'<iframe[^>]*?bot[^>]*?src=["\']([^"\']*)["\'][^>]*?></iframe>', post.content, re.IGNORECASE)
            for iframe_src in bot_iframes:
                logger.info(f"Found bot iframe with source: {iframe_src}")
                
                # Create a safer replacement
                safe_div = f'<div class="bot-placeholder" style="border:1px solid #ccc; padding:10px; text-align:center; margin:10px 0;">\n'
                safe_div += f'  <p>Bot content from: {iframe_src}</p>\n'
                safe_div += f'  <p><a href="{iframe_src}" target="_blank" rel="noopener">Open Bot in New Window</a></p>\n'
                safe_div += f'</div>'
                
                # Replace the iframe with the safer div
                post.content = re.sub(
                    r'<iframe[^>]*?bot[^>]*?src=["\']' + re.escape(iframe_src) + r'["\'][^>]*?></iframe>',
                    safe_div,
                    post.content,
                    flags=re.IGNORECASE
                )
        
        # Use BeautifulSoup to fix HTML structure
        try:
            soup = BeautifulSoup(post.content, 'html.parser')
            pretty_html = soup.prettify()
            
            # In some cases, BeautifulSoup adds extra whitespace or breaks layout
            # If content has changed significantly, use a more targeted approach
            if abs(len(pretty_html) - len(post.content)) > len(post.content) * 0.2:
                logger.warning("BeautifulSoup changed content significantly, using manual fixes instead")
                
                # Manual fixes for unclosed tags
                fixed_content = post.content
                for tag in ['p', 'div', 'span', 'a', 'strong', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li']:
                    open_tags = fixed_content.lower().count(f"<{tag}")
                    close_tags = fixed_content.lower().count(f"</{tag}>")
                    
                    if open_tags > close_tags:
                        logger.info(f"Adding {open_tags - close_tags} missing </{tag}> tags")
                        fixed_content += f"</{tag}>" * (open_tags - close_tags)
                
                post.content = fixed_content
            else:
                # Use BeautifulSoup's corrected HTML
                post.content = pretty_html
        
        except Exception as e:
            logger.error(f"Error processing HTML with BeautifulSoup: {str(e)}")
            # Fall back to simple fixes
            fixed_content = post.content
            for tag in ['p', 'div', 'span', 'a', 'strong', 'em']:
                open_tags = fixed_content.lower().count(f"<{tag}")
                close_tags = fixed_content.lower().count(f"</{tag}>")
                
                if open_tags > close_tags:
                    logger.info(f"Adding {open_tags - close_tags} missing </{tag}> tags")
                    fixed_content += f"</{tag}>" * (open_tags - close_tags)
            
            post.content = fixed_content
        
        # Check if content has changed
        if post.content != original_content:
            logger.info(f"Fixed post {post_id}, saving changes")
            try:
                db.session.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving changes: {str(e)}")
                db.session.rollback()
                return False
        else:
            logger.info(f"No changes needed for post {post_id}")
            return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_post_html.py [show|fix|fix-all] [post_id]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'show' and len(sys.argv) > 2:
        post_id = int(sys.argv[2])
        get_post_content(post_id)
    elif command == 'fix' and len(sys.argv) > 2:
        post_id = int(sys.argv[2])
        if fix_post_html(post_id):
            logger.info(f"Successfully fixed post {post_id}")
        else:
            logger.info(f"No changes made to post {post_id}")
    elif command == 'fix-all':
        fix_all_posts()
    else:
        print("Invalid command")
        print("Usage: python fix_post_html.py [show|fix|fix-all] [post_id]")
        sys.exit(1)

if __name__ == "__main__":
    main() 