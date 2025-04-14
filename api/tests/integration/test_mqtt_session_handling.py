import pytest
import paho.mqtt.client as mqtt
import json
import uuid
import time
import logging
import base64
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

# Assuming your services and models are importable from the test environment
# You might need to adjust sys.path or use relative imports depending on your test runner setup
from config import Config  # To get MQTT broker details
# Import models needed for assertions
from models.notification import NotificationType, SeverityLevel
from models.access_log import AccessLog
from models.verification_image import VerificationImage
from models.notification_history import NotificationHistory
# Import the actual Session Pydantic model for creating payloads
from models.session import Session as SessionPayloadModel

# --- Constants ---
MQTT_BROKER = Config.MQTT_BROKER_ADDRESS
MQTT_PORT = Config.MQTT_BROKER_PORT
SESSION_TOPIC = "campus/security/session"
UNLOCK_TOPIC = "campus/security/unlock"

TEST_TIMEOUT = 10  # Seconds to wait for processing

# A known RFID tag and employee ID from your sample_data.sql (replace if needed)
KNOWN_RFID_TAG = "0001868767"
# Replace with actual UUID from sample_data
KNOWN_EMPLOYEE_ID = "a1b2c3d4-e5f6-7890-1234-567890abcdef"
UNKNOWN_RFID_TAG = "0000000000"

# Sample valid base64 image (replace with a small, actual base64 image string if needed)
# You can generate one online or using: python -c "import base64; print(base64.b64encode(open('test.jpg', 'rb').read()).decode())"
SAMPLE_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# --- Pytest Fixtures ---


@pytest.fixture(scope="module")
def mqtt_publisher():
    """Provides a connected MQTT client for publishing test messages."""
    client_id = f"pytest-publisher-{uuid.uuid4()}"
    client = mqtt.Client(client_id=client_id)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        yield client  # Give the client to the test
    finally:
        print("Disconnecting MQTT Publisher")
        client.loop_stop()
        client.disconnect()

# Note: A real DB connection fixture for assertions is complex to set up here.
# We will rely on checking the *mocks* that interact with the DB service for now,
# assuming the DB service methods themselves are unit-tested elsewhere.
# If you have a test DB setup, you'd add a fixture here to get a session.

# --- Test Functions ---

# Use patch to mock external dependencies *where they are used*
# Patching methods on the specific service instances might be tricky without access to the app context
# Easier to patch the class methods globally for the test run.


@patch('services.face_recognition_client.FaceRecognitionClient.get_embedding')
@patch('services.face_recognition_client.FaceRecognitionClient.verify_embeddings')
# Mock the sending methods
@patch('services.notification_service.NotificationService._send_sms')
@patch('services.notification_service.NotificationService._send_ntfy')
@patch('services.database.DatabaseService.get_employee_by_rfid')
@patch('services.database.DatabaseService.save_verification_image')
@patch('services.database.DatabaseService.log_access_attempt')
@patch('services.database.DatabaseService.save_notification_to_history')
# Mock the MQTT publish method used by the service
@patch('paho.mqtt.client.Client.publish')
def test_successful_rfid_face_verification(
    mock_mqtt_publish,
    mock_save_notification_history,
    mock_log_access_attempt,
    mock_save_verification_image,
    mock_get_employee_by_rfid,
    mock_send_ntfy,
    mock_send_sms,
    mock_verify_embeddings,
    mock_get_embedding,
    mqtt_publisher  # Use the fixture
):
    """Test the flow for a successful RFID + Face verification."""
    print("\n--- Running test_successful_rfid_face_verification ---")
    # --- Arrange ---
    test_session_id = str(uuid.uuid4())
    mock_embedding = [0.1] * 512  # Example embedding

    # Configure Face Client Mocks
    mock_get_embedding.return_value = mock_embedding
    mock_verify_embeddings.return_value = {
        "is_match": True, "confidence": 0.95}

    # Configure DB Mocks
    # Simulate finding the employee
    mock_employee = MagicMock()
    # Ensure it's a UUID object
    mock_employee.id = uuid.UUID(KNOWN_EMPLOYEE_ID)
    mock_employee.name = "Test Employee"
    mock_employee.face_embedding = [0.1] * 512  # Needs a stored embedding
    mock_get_employee_by_rfid.return_value = mock_employee

    # Simulate successful DB saves (can return mock objects if needed)
    mock_save_verification_image.return_value = MagicMock(id=uuid.uuid4())
    mock_log_access_attempt.return_value = MagicMock()
    mock_save_notification_history.return_value = MagicMock()

    # Create Test Payload
    payload = {
        "device_id": "test-esp32",
        "session_id": test_session_id,
        "timestamp": int(time.time() * 1000),  # Milliseconds
        "session_duration": 1500,
        "image_size": len(base64.b64decode(SAMPLE_IMAGE_B64)),
        "image_data": SAMPLE_IMAGE_B64,
        "rfid_detected": True,
        "rfid_tag": KNOWN_RFID_TAG,
        "face_detected": True,  # Assuming face was detected by ESP32
        "free_heap": 50000,
        "state": "SESSION"  # Or appropriate state from ESP32
    }
    payload_json = json.dumps(payload)

    # --- Act ---
    print(f"Publishing successful verification message to {SESSION_TOPIC}")
    mqtt_publisher.publish(SESSION_TOPIC, payload=payload_json, qos=1)
    print("Waiting for processing...")
    time.sleep(TEST_TIMEOUT)  # Allow time for message processing

    # --- Assert ---
    print("Asserting outcomes...")
    # 1. DB Checks (via mocks)
    mock_get_employee_by_rfid.assert_called_once_with(KNOWN_RFID_TAG)
    mock_save_verification_image.assert_called_once()
    mock_log_access_attempt.assert_called_once_with(
        session_id=test_session_id,
        verification_method="RFID+FACE",
        access_granted=True,
        employee_id=mock_employee.id,  # Check if correct employee ID was used
        verification_confidence=0.95,
        verification_image_id=mock_save_verification_image.return_value.id
    )
    # 2. Face Client Checks
    mock_get_embedding.assert_called_once_with(SAMPLE_IMAGE_B64)
    mock_verify_embeddings.assert_called_once_with(
        mock_embedding, mock_employee.face_embedding)

    # 3. Notification Checks
    # Check NotificationService sending methods were NOT called for INFO
    mock_send_sms.assert_not_called()
    mock_send_ntfy.assert_not_called()  # Assuming INFO severity doesn't trigger ntfy
    # Check notification was logged to history
    mock_save_notification_history.assert_called_once()
    # Inspect the notification object passed to save_notification_to_history
    call_args, _ = mock_save_notification_history.call_args
    saved_notification = call_args[0]
    assert saved_notification.event_type == NotificationType.ACCESS_GRANTED
    assert saved_notification.severity == SeverityLevel.INFO
    assert saved_notification.session_id == test_session_id
    assert saved_notification.user_id == KNOWN_EMPLOYEE_ID
    # Check the status set by MQTTService
    assert saved_notification.status == "Sent_Success"

    # 4. MQTT Unlock Check
    mock_mqtt_publish.assert_called_once()
    # Check the arguments passed to the publish mock
    publish_args, publish_kwargs = mock_mqtt_publish.call_args
    assert publish_args[0] == UNLOCK_TOPIC  # Check topic
    unlock_payload = json.loads(publish_kwargs['payload'])
    assert unlock_payload["command"] == "UNLOCK"
    assert unlock_payload["session_id"] == test_session_id
    assert publish_kwargs['qos'] == 1

    print("test_successful_rfid_face_verification PASSED")

# --- Placeholder for other tests ---

# @patch(...) # Add necessary patches


def test_face_verification_failure():
    # Similar structure to above, but:
    # - mock_verify_embeddings returns {"is_match": False, "confidence": 0.5}
    # - Assert log_access_attempt has access_granted=False
    # - Assert correct notification (FACE_NOT_RECOGNIZED, WARNING/CRITICAL) is sent/logged
    # - Assert mock_mqtt_publish (unlock) is NOT called
    pass

# @patch(...)


def test_rfid_not_found():
    # Similar structure, but:
    # - Use UNKNOWN_RFID_TAG in payload
    # - mock_get_employee_by_rfid returns None
    # - Assert log_access_attempt has access_granted=False, method maybe 'INCOMPLETE_DATA' or 'RFID_ONLY_ATTEMPT' depending on logic
    # - Assert correct notification (RFID_NOT_FOUND, WARNING) is sent/logged
    # - Assert mock_mqtt_publish (unlock) is NOT called
    pass

# Add more tests:
# - No image data provided
# - Face embedding fails
# - System error during processing
# - Emergency topic message
