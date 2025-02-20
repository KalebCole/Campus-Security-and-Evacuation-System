import os
import requests
import time
import logging
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:5000/api"
HEADERS = {"Content-Type": "application/json"}

'''
System State Tests
1. System Inactive Test

    Send RFID without activating system
    Send image without activating system
    Verify both return "System not activated" error

2. System Activation Flow
    Activate system
    Verify system state is active
    Deactivate system
    Verify system state is inactive

3. System Timeout Test
    Activate system
    Wait for timeout
    Verify system state is inactive

'''


'''
Basic Authentication Flows

1. Successful Authentication
    Activate system
    Send RFID (using "123456" - Bob's RFID)
    Verify RFID_RECOGNIZED notification
    Send matching face image
    Verify ACCESS_GRANTED notification
    
2. Image First Authentication
    Activate system
    Send face image first
    Verify FACE_RECOGNIZED notification
    Send matching RFID
    Verify ACCESS_GRANTED notification
'''


class SystemStateTests:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.logger = logging.getLogger(__name__)

    def _activate_system(self):
        """Helper method to activate the system"""
        response = requests.get(f"{self.base_url}/system/activate")
        return response.status_code == 200

    def _deactivate_system(self):
        """Helper method to deactivate the system"""
        response = requests.get(f"{self.base_url}/system/deactivate")
        return response.status_code == 200

    def _send_rfid(self, rfid_tag):
        """Helper method to send RFID data"""
        data = {"rfid_tag": rfid_tag}
        response = requests.post(f"{self.base_url}/rfid", json=data)
        return response

    def _send_image(self, image_path):
        """Helper method to send image data
        Args:
            image_path (str): Path to image file relative to the tests directory
        """
        # Get absolute path to test images directory
        test_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(test_dir, "test_images", image_path)

        # Verify file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Test image not found: {image_path}")

        # Open and send image file
        with open(image_path, 'rb') as image_file:
            files = {
                'imageFile': ('test_image.jpg', image_file, 'image/jpeg')
            }
            data = {'session_id': self.current_session_id} if hasattr(
                self, 'current_session_id') else {}
            response = requests.post(
                f"{self.base_url}/image",
                files=files,
                data=data
            )
        return response

    def test_system_inactive(self):
        """Test 1: System Inactive Test"""
        self.logger.info("Running System Inactive Test...")

        # Ensure system is deactivated
        self._deactivate_system()

        # Test RFID when system is inactive
        rfid_response = self._send_rfid("123456")
        self.logger.debug(f"RFID response: {rfid_response.json()}")
        assert rfid_response.status_code == 400, "RFID should be rejected when system is inactive"
        assert rfid_response.json()["message"] == "System not activated"
        self.logger.info("✓ RFID rejected when system inactive")

        # Test image when system is inactive
        image_response = self._send_image("image.png")
        assert image_response.status_code == 400, "Image should be rejected when system is inactive"
        assert image_response.json()["message"] == "System not activated"
        self.logger.info("✓ Image rejected when system inactive")

    def test_system_activation_flow(self):
        """Test 2: System Activation Flow"""
        self.logger.info("Running System Activation Flow Test...")

        # Test activation
        assert self._activate_system(), "System activation failed"
        self.logger.info("✓ System activated successfully")

        # Verify system is active by sending a valid RFID
        rfid_response = self._send_rfid("123456")
        assert rfid_response.status_code == 202, "RFID should be accepted when system is active"
        self.logger.info("✓ System confirmed active")

        # Test deactivation
        assert self._deactivate_system(), "System deactivation failed"
        self.logger.info("✓ System deactivated successfully")

        # Verify system is inactive
        rfid_response = self._send_rfid("123456")
        assert rfid_response.status_code == 400, "RFID should be rejected after deactivation"
        self.logger.info("✓ System confirmed inactive")

    def test_system_timeout(self):
        """Test 3: System Timeout Test"""
        self.logger.info("Running System Timeout Test...")

        # Activate system
        assert self._activate_system(), "System activation failed"
        self.logger.info("✓ System activated successfully")

        # Wait for timeout (SESSION_TIMEOUT is 15 seconds)
        timeout_duration = 16  # slightly longer than SESSION_TIMEOUT
        self.logger.info(f"Waiting {timeout_duration} seconds for timeout...")
        time.sleep(timeout_duration)

        # Verify system is inactive after timeout
        rfid_response = self._send_rfid("123456")
        assert rfid_response.status_code == 400, "System should be inactive after timeout"
        assert rfid_response.json()["message"] == "System not activated"
        self.logger.info("✓ System timed out successfully")


def run_system_state_tests():
    """Run all system state tests"""
    logger.info("Starting system state tests...")
    tests = SystemStateTests()

    try:
        # tests.test_system_inactive()
        # tests.test_system_activation_flow()
        tests.test_system_timeout()
        logger.info("All system state tests passed! ✨")
    except AssertionError as e:
        logger.error(f"Test failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    run_system_state_tests()
