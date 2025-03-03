import os
import sys
# Add server directory to path for imports
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)
from data.session import Session, SessionType
from app_config import Config
from worker_manager import WorkerManager
from session_manager import SessionManager
import time
import logging
import requests
import uuid
from datetime import datetime



# Import from server modules - corrected imports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:5000/api"


def test_cleanup_worker():
    """Test the cleanup worker thread"""
    logger.info("\n=== 🧪 Testing Cleanup Worker Thread ===")

    # Start the cleanup task with a short interval
    logger.info("Starting cleanup task...")
    worker_manager = WorkerManager(SessionManager())
    cleanup_thread = worker_manager.start_cleanup_task(
        interval=5)  # 5 second interval

    if cleanup_thread and cleanup_thread.is_alive():
        logger.info("✅ Cleanup thread started successfully")
    else:
        logger.error("❌ Cleanup thread failed to start")
        return False

    # Run for a few seconds
    logger.info("Running cleanup thread for 3 seconds...")
    time.sleep(3)

    # Stop the cleanup task
    stop_result = worker_manager.stop_cleanup_task()
    if stop_result:
        logger.info("✅ Cleanup thread stopped successfully")
    else:
        logger.error("❌ Failed to stop cleanup thread")

    logger.info("=== 🎉 Cleanup Worker Test Complete ===\n")
    return True


def test_server_activation():
    """Test system activation via API"""
    logger.info("\n=== 🧪 Testing System Activation ===")

    # First deactivate the system
    deactivate_response = requests.get(f"{BASE_URL}/deactivate")
    logger.info(
        f"System deactivation status: {deactivate_response.status_code}")

    # Then activate it
    activate_response = requests.get(f"{BASE_URL}/activate")
    if activate_response.status_code == 200:
        logger.info("✅ System activated successfully via API")
    else:
        logger.error(
            f"❌ Failed to activate system: {activate_response.status_code}")
        return False

    # Create a test session
    rfid_data = {"rfid_tag": "123456"}  # Use a valid RFID from mock DB
    rfid_response = requests.post(f"{BASE_URL}/rfid", json=rfid_data)

    if rfid_response.status_code == 202:
        session_id = rfid_response.json().get("session_id")
        logger.info(f"✅ Created test session: {session_id}")
    else:
        logger.error(
            f"❌ Failed to create session: {rfid_response.status_code}")
        return False

    # Cleanup
    requests.get(f"{BASE_URL}/deactivate")
    logger.info("System deactivated")

    logger.info("=== 🎉 System Activation Test Complete ===\n")
    return True


if __name__ == "__main__":
    print("\n🧪 Running Session Management Tests 🧪\n")

    # Run individual tests - comment out ones you don't want to run
    test_cleanup_worker()
    # test_server_activation()

    print("\n✅ All tests completed\n")
