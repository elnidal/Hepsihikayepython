#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_default_image():
    """Create a default image for posts that don't have an image"""
    try:
        # Define the path for the default image
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        default_image_path = os.path.join(uploads_dir, 'default_post_image.png')
        
        # Create the directory if it doesn't exist
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
            logger.info(f"Created uploads directory at: {uploads_dir}")
        
        # Check if the default image already exists
        if os.path.exists(default_image_path):
            logger.info(f"Default image already exists at: {default_image_path}")
            return default_image_path
        
        # Create a new image with a teal background (similar to the one in the screenshot)
        width, height = 800, 600
        background_color = (26, 188, 156)  # Teal color
        image = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font, fall back to default if not available
        try:
            # Try to use a system font
            font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'  # Common on macOS
            if not os.path.exists(font_path):
                font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'  # Common on Linux
            
            if os.path.exists(font_path):
                title_font = ImageFont.truetype(font_path, 120)
                subtitle_font = ImageFont.truetype(font_path, 40)
            else:
                # Fall back to default font
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                
        except Exception as e:
            logger.warning(f"Could not load font: {str(e)}")
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # Add text to the image
        title_text = "Hikaye"
        subtitle_text = "HepsiHikaye.net"
        
        # Calculate text position to center it
        title_width = draw.textlength(title_text, font=title_font)
        title_position = ((width - title_width) // 2, height // 2 - 80)
        
        subtitle_width = draw.textlength(subtitle_text, font=subtitle_font)
        subtitle_position = ((width - subtitle_width) // 2, height // 2 + 80)
        
        # Draw the text in white
        draw.text(title_position, title_text, fill=(255, 255, 255), font=title_font)
        draw.text(subtitle_position, subtitle_text, fill=(255, 255, 255), font=subtitle_font)
        
        # Save the image
        image.save(default_image_path)
        logger.info(f"Created default image at: {default_image_path}")
        
        return default_image_path
        
    except Exception as e:
        logger.error(f"Error creating default image: {str(e)}")
        return None

if __name__ == "__main__":
    default_image = create_default_image()
    if default_image:
        print(f"Default image created successfully at: {default_image}")
    else:
        print("Failed to create default image") 