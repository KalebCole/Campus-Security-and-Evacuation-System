import os
import sys
# Add server directory to path for imports
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)
from app_config import Config
import unittest
import requests
import logging

# Add server directory to path for imports
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TestBasicRoutes(unittest.TestCase):
    """Test basic routes of the API"""

    def test_test_endpoint(self):
        """Test the /test endpoint returns a success response"""
        logger.info("Testing /test endpoint...")

        # Construct the full URL using the base URL from Config
        base_url = Config.SERVER_BASE_URL if hasattr(
            Config, 'SERVER_BASE_URL') else "http://localhost:5000"
        url = f"{base_url}/api/test"

        try:
            # Send GET request to the test endpoint
            response = requests.get(url)

            # Check status code
            self.assertEqual(response.status_code, 200,
                             f"Expected status code 200, got {response.status_code}")

            # Check response content
            data = response.json()
            self.assertIn("message", data,
                          "Response should contain 'message' field")
            self.assertEqual(data["message"], "Routes Blueprint is working!",
                             f"Expected 'Routes Blueprint is working!', got '{data['message']}'")

            logger.info("✅ Test endpoint test passed!")

        except requests.RequestException as e:
            self.fail(f"Request failed: {e}")

        except Exception as e:
            self.fail(f"Unexpected error: {e}")


def run_test():
    """Run the test directly without unittest runner"""
    test = TestBasicRoutes()
    try:
        test.test_test_endpoint()
        logger.info("All tests passed!")
        return True
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Option 1: Run with unittest (more verbose output)
    # unittest.main()

    # Option 2: Run directly (simpler output)
    run_test()
