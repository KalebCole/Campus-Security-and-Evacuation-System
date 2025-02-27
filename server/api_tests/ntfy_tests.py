import os
import requests
import time
import logging
import sys
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


class NotificationDemoTests:
    """Test class for demonstrating all notification types with real NTFY messages"""

    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.logger = logging.getLogger(__name__)
        self.current_session_id = None

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
        data = {"rfid_tag": rfid_tag, "session_id": self.current_session_id}
        response = requests.post(f"{self.base_url}/rfid", json=data)
        if response.status_code == 202:
            response_data = response.json()
            self.current_session_id = response_data.get('session_id')
        return response

    def _send_image(self, image_path):
        """Helper method to send image data"""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(test_dir, "test_images", image_path)
        logger.info(f"Sending image: {image_path}")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Test image not found: {image_path}")

        with open(image_path, 'rb') as image_file:
            files = {'imageFile': ('test_image.jpg', image_file, 'image/jpeg')}
            data = {
                'session_id': self.current_session_id} if self.current_session_id else {}
            response = requests.post(
                f"{self.base_url}/image", files=files, data=data)
            if response.status_code == 202:
                response_data = response.json()
                self.current_session_id = response_data.get('session_id')
            return response


def run_rfid_not_found_test():
    """Demo RFID_NOT_FOUND notification"""
    logger.info("\n=== 📱 Running RFID Not Found Test ===")
    demo = NotificationDemoTests()
    try:
        demo._activate_system()
        response = demo._send_rfid("non_existent_rfid")
        assert response.status_code in [
            404, 400], "Expected error response for invalid RFID"
        logger.info("✅ RFID Not Found test complete - Check NTFY!")
        time.sleep(3)  # Wait for notification
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
    finally:
        demo._deactivate_system()


def run_rfid_recognized_test():
    """Demo RFID_RECOGNIZED notification"""
    logger.info("\n=== 📱 Running RFID Recognized Test ===")
    demo = NotificationDemoTests()
    try:
        demo._activate_system()
        response = demo._send_rfid("123456")  # Bob's RFID
        assert response.status_code == 202, "Expected acceptance of valid RFID"
        logger.info("✅ RFID Recognized test complete - Check NTFY!")
        time.sleep(3)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
    finally:
        demo._deactivate_system()


def run_face_recognized_test():
    """Demo FACE_RECOGNIZED notification"""
    logger.info("\n=== 📱 Running Face Recognized Test ===")
    demo = NotificationDemoTests()
    try:
        demo._activate_system()
        response = demo._send_image("bob.png")
        assert response.status_code == 202, "Expected acceptance of valid image"
        logger.info("✅ Face Recognized test complete - Check NTFY!")
        time.sleep(3)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
    finally:
        demo._deactivate_system()


def run_access_granted_test():
    """Demo ACCESS_GRANTED notification"""
    logger.info("\n=== 📱 Running Access Granted Test ===")
    demo = NotificationDemoTests()
    try:
        demo._activate_system()
        rfid_response = demo._send_rfid("123456")  # Bob's RFID
        image_response = demo._send_image("bob.png")  # Bob's face
        assert rfid_response.status_code == 202 and image_response.status_code == 202
        logger.info("✅ Access Granted test complete - Check NTFY!")
        time.sleep(3)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
    finally:
        demo._deactivate_system()


def run_face_mismatch_test():
    """Demo FACE_MISMATCH notification"""
    logger.info("\n=== 📱 Running Face Mismatch Test ===")
    demo = NotificationDemoTests()
    try:
        demo._activate_system()
        rfid_response = demo._send_rfid("123456")  # Bob's RFID
        image_response = demo._send_image("charlie.png")  # Wrong face
        assert rfid_response.status_code == 202 and image_response.status_code == 202
        logger.info("✅ Face Mismatch test complete - Check NTFY!")
        time.sleep(3)
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
    finally:
        demo._deactivate_system()


def run_all_notification_tests():
    """Run all notification tests in sequence"""
    logger.info("\n=== 🚀 Starting All Notification Tests ===")

    # Verify test images exist
    test_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(test_dir, "test_images")
    required_images = ["bob.png", "charlie.png"]
    missing = [img for img in required_images if not os.path.exists(
        os.path.join(images_dir, img))]

    if missing:
        logger.error(f"❌ Missing test images: {', '.join(missing)}")
        logger.error(f"Please add images to: {images_dir}")
        return False

    # Run all tests
    run_rfid_not_found_test()
    run_rfid_recognized_test()
    run_face_recognized_test()
    run_access_granted_test()
    run_face_mismatch_test()

    logger.info("\n=== 🎉 All Notification Tests Complete ===")
    return True


if __name__ == "__main__":
    # Uncomment the specific test you want to run
    run_rfid_not_found_test()
    # run_rfid_recognized_test()
    # run_face_recognized_test()
    # run_access_granted_test()
    # run_face_mismatch_test()

    # Or run all tests
    # run_all_notification_tests()
