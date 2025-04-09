import unittest
import time
import json
from mqtt_handler import MQTTHandler
from session_handler import SessionHandler


class TestMQTTHandlers(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.mqtt_handler = MQTTHandler(
            broker_address="localhost", broker_port=1883)
        self.session_handler = SessionHandler(
            broker_address="localhost", broker_port=1883)

    def test_01_connection(self):
        """Test basic MQTT connection"""
        try:
            self.mqtt_handler.connect()
            self.session_handler.connect()
            time.sleep(2)  # Wait for connection to establish
            self.assertTrue(self.mqtt_handler.client.is_connected())
            self.assertTrue(self.session_handler.client.is_connected())
        finally:
            self.mqtt_handler.disconnect()
            self.session_handler.disconnect()

    def test_02_session_creation(self):
        """Test session creation and retrieval"""
        try:
            self.mqtt_handler.connect()
            self.session_handler.connect()
            time.sleep(2)

            # Test creating a session
            device_id = "test_device_01"
            session_data = {
                "device_id": device_id,
                "status": "active",
                "timestamp": "2024-04-09T12:00:00Z"
            }

            # Update session through session handler
            self.session_handler.update_session(device_id, session_data)

            # Retrieve session through session handler
            retrieved_session = self.session_handler.get_session(device_id)

            self.assertIsNotNone(retrieved_session)
            self.assertEqual(retrieved_session["device_id"], device_id)
            self.assertEqual(retrieved_session["status"], "active")

        finally:
            self.mqtt_handler.disconnect()
            self.session_handler.disconnect()

    def test_03_message_handling(self):
        """Test basic message handling"""
        try:
            self.mqtt_handler.connect()
            self.session_handler.connect()
            time.sleep(2)

            # Test RFID message
            rfid_message = {
                "device_id": "test_device_01",
                "rfid_tag": "123456",
                "timestamp": "2024-04-09T12:00:00Z"
            }

            # Publish RFID message
            self.mqtt_handler.client.publish(
                "campus/security/rfid", json.dumps(rfid_message))
            time.sleep(1)  # Wait for message to be processed

            # Verify session was created/updated
            session = self.session_handler.get_session("test_device_01")
            self.assertIsNotNone(session)

        finally:
            self.mqtt_handler.disconnect()
            self.session_handler.disconnect()

    def test_04_disconnection(self):
        """Test proper disconnection"""
        self.mqtt_handler.connect()
        self.session_handler.connect()
        time.sleep(2)

        self.mqtt_handler.disconnect()
        self.session_handler.disconnect()

        time.sleep(1)  # Wait for disconnection to complete
        self.assertFalse(self.mqtt_handler.client.is_connected())
        self.assertFalse(self.session_handler.client.is_connected())


if __name__ == '__main__':
    unittest.main()
