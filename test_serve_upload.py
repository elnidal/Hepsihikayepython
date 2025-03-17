import os
import sys
import logging
import requests
from urllib.parse import urljoin
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_serve_upload():
    """Test the serve_upload function with various scenarios"""
    logger.info("Starting test of serve_upload function...")
    
    # Use the development server URL
    base_url = "http://127.0.0.1:5000"
    
    # Test cases
    test_cases = [
        # Existing image
        {"path": "/static/uploads/default_post_image.png", "expected_status": 200},
        # Non-existent image - should redirect to default
        {"path": "/uploads/non_existent_image.png", "expected_status": 302},
        # The problematic images from the logs
        {"path": "/uploads/1742154623_0_1.png", "expected_status": 302},
        {"path": "/uploads/1742154009_0_1.png", "expected_status": 302}
    ]
    
    logger.info("Starting Flask development server for testing...")
    print("\nPlease run the Flask development server in another terminal:")
    print("flask run\n")
    input("Press Enter to continue once the server is running...")
    
    for test_case in test_cases:
        url = urljoin(base_url, test_case["path"])
        try:
            logger.info(f"Testing URL: {url}")
            response = requests.get(url, allow_redirects=False)
            
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code == test_case["expected_status"]:
                logger.info(f"Test passed for {test_case['path']}")
            else:
                logger.warning(f"Test failed for {test_case['path']} - Expected {test_case['expected_status']}, got {response.status_code}")
                
            if response.status_code == 302:
                redirect_url = response.headers.get('Location')
                logger.info(f"Redirect URL: {redirect_url}")
                
                # Follow the redirect
                if redirect_url:
                    redirect_response = requests.get(urljoin(base_url, redirect_url))
                    logger.info(f"Redirect response status: {redirect_response.status_code}")
        
        except Exception as e:
            logger.error(f"Error testing {test_case['path']}: {str(e)}")
    
    logger.info("All tests completed")

if __name__ == "__main__":
    test_serve_upload() 