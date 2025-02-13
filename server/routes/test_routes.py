import unittest
from unittest.mock import patch, call
import time
import threading
from datetime import datetime
from routes.routes import monitor_sessions, session_data, SESSION_TIMEOUT
from notifications.notification_service import NotificationType
import routes.routes  # Import the module to access its variables


class TestMonitorSessions(unittest.TestCase):

    def setUp(self):
        # Clear session data before each test
        session_data.clear()
        routes.routes.session_data.clear()  # Clear the session_data in routes.py

    # replaces handle_rfid_and_image with a mock object
    @patch('routes.routes.handle_rfid_and_image')
    @patch('routes.routes.handle_rfid_only')
    @patch('routes.routes.handle_image_only')
    def test_monitor_sessions_rfid_and_embedding(self, mock_handle_image_only, mock_handle_rfid_only, mock_handle_rfid_and_image):
        """Test when both RFID and embedding are available."""
        session_id = "test_session"
        session_data[session_id] = {
            "rfid": "123",
            "embedding": [0.1] * 128,
            "timestamp": time.time()
        }
        routes.routes.session_data[session_id] = session_data[session_id]

        # Create a thread and run monitor_sessions for a short duration
        monitor_thread = threading.Thread(target=monitor_sessions)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(0.1)  # Give the monitor thread some time to run

        # Assert that handle_rfid_and_image was called with the correct arguments
        mock_handle_rfid_and_image.assert_called_once_with(
            "123", [0.1] * 128, session_id)
        self.assertEqual(mock_handle_rfid_only.call_count, 0)
        self.assertEqual(mock_handle_image_only.call_count, 0)
        self.assertNotIn(session_id, session_data)
        self.assertNotIn(session_id, routes.routes.session_data)

    @patch('routes.routes.handle_rfid_and_image')
    @patch('routes.routes.handle_rfid_only')
    @patch('routes.routes.handle_image_only')
    def test_monitor_sessions_rfid_and_image(self, mock_handle_image_only, mock_handle_rfid_only, mock_handle_rfid_and_image):
        """Test when both RFID and image are available."""
        session_id = "test_session"
        image_data = "test_image_data"
        session_data[session_id] = {
            "rfid": "123",
            "image": image_data,
            "timestamp": time.time()
        }
        routes.routes.session_data[session_id] = session_data[session_id]

        # Create a thread and run monitor_sessions for a short duration
        monitor_thread = threading.Thread(target=monitor_sessions)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(0.1)  # Give the monitor thread some time to run

        # Assert that handle_rfid_and_image was called with the correct arguments
        mock_handle_rfid_and_image.assert_called_once_with(
            "123", image_data, session_id)
        self.assertEqual(mock_handle_rfid_only.call_count, 0)
        self.assertEqual(mock_handle_image_only.call_count, 0)
        self.assertNotIn(session_id, session_data)
        self.assertNotIn(session_id, routes.routes.session_data)

    @patch('routes.routes.handle_rfid_and_image')
    @patch('routes.routes.handle_rfid_only')
    @patch('routes.routes.handle_image_only')
    def test_monitor_sessions_rfid_only(self, mock_handle_image_only, mock_handle_rfid_only, mock_handle_rfid_and_image):
        """Test when only RFID is available."""
        session_id = "test_session"
        session_data[session_id] = {
            "rfid": "123",
            "timestamp": time.time()
        }
        routes.routes.session_data[session_id] = session_data[session_id]

        # Create a thread and run monitor_sessions for a short duration
        monitor_thread = threading.Thread(target=monitor_sessions)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(0.1)  # Give the monitor thread some time to run

        # Assert that handle_rfid_only was called with the correct arguments
        mock_handle_rfid_only.assert_called_once_with("123", session_id)
        self.assertEqual(mock_handle_rfid_and_image.call_count, 0)
        self.assertEqual(mock_handle_image_only.call_count, 0)

    @patch('routes.routes.handle_rfid_and_image')
    @patch('routes.routes.handle_rfid_only')
    @patch('routes.routes.handle_image_only')
    def test_monitor_sessions_image_only(self, mock_handle_image_only, mock_handle_rfid_only, mock_handle_rfid_and_image):
        """Test when only image is available."""
        session_id = "test_session"
        image_data = "test_image_data"
        session_data[session_id] = {
            "image": image_data,
            "timestamp": time.time()
        }
        routes.routes.session_data[session_id] = session_data[session_id]

        # Create a thread and run monitor_sessions for a short duration
        monitor_thread = threading.Thread(target=monitor_sessions)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(0.1)  # Give the monitor thread some time to run

        # Assert that handle_image_only was called with the correct arguments
        mock_handle_image_only.assert_called_once_with(image_data, session_id)
        self.assertEqual(mock_handle_rfid_and_image.call_count, 0)
        self.assertEqual(mock_handle_rfid_only.call_count, 0)

    # @patch('routes.routes.handle_rfid_and_image')
    # @patch('routes.routes.handle_rfid_only')
    # @patch('routes.routes.handle_image_only')
    # def test_monitor_sessions_expired_session(self, mock_handle_image_only, mock_handle_rfid_only, mock_handle_rfid_and_image):
    #     """Test that expired sessions are cleaned up."""
    #     session_id = "test_session"
    #     session_data[session_id] = {
    #         "rfid": "123",
    #         "timestamp": time.time() - SESSION_TIMEOUT - 10  # Expired timestamp
    #     }
    #     routes.routes.session_data[session_id] = session_data[session_id]

    #     # Create a thread and run monitor_sessions for a short duration
    #     monitor_thread = threading.Thread(target=monitor_sessions)
    #     monitor_thread.daemon = True
    #     monitor_thread.start()
    #     time.sleep(1)  # Give the monitor thread some time to run

    #     # Assert that the session was cleaned up
    #     self.assertEqual(mock_handle_rfid_and_image.call_count, 0)
    #     self.assertEqual(mock_handle_rfid_only.call_count, 0)
    #     self.assertEqual(mock_handle_image_only.call_count, 0)
    #     self.assertNotIn(session_id, session_data)
    #     self.assertNotIn(session_id, routes.routes.session_data)

    @patch('routes.routes.handle_rfid_and_image')
    @patch('routes.routes.handle_rfid_only')
    @patch('routes.routes.handle_image_only')
    def test_monitor_sessions_no_data(self, mock_handle_image_only, mock_handle_rfid_only, mock_handle_rfid_and_image):
        """Test when there is no data in session."""
        # Create a thread and run monitor_sessions for a short duration
        monitor_thread = threading.Thread(target=monitor_sessions)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(1)  # Give the monitor thread some time to run

        # Assert that the session was cleaned up
        self.assertEqual(mock_handle_rfid_and_image.call_count, 0)
        self.assertEqual(mock_handle_rfid_only.call_count, 0)
        self.assertEqual(mock_handle_image_only.call_count, 0)
