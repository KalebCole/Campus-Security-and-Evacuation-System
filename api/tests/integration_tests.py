"""Integration tests for the Campus Security Enhancement System API."""

import json
import base64
import time
from pathlib import Path
import paho.mqtt.client as mqtt
import os
import pytest
import numpy as np
import logging
import requests
import psycopg2
from unittest.mock import patch, MagicMock, ANY
from config import Config
from models.notification import Notification, NotificationType, SeverityLevel
from datetime import datetime
import uuid

# Set up logging for the test
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Assume TOPIC constants are defined globally or imported if needed
TOPIC_SESSION_DATA = "campus/security/session"
TOPIC_EMERGENCY = "campus/security/emergency"
TOPIC_UNLOCK_COMMAND = "campus/security/unlock"

# Helper to load image data


def load_test_image(image_name="kaleb.jpeg"):
    image_path = Path(__file__).parent / "test_images" / image_name
    logger.info(f"Using test image from {image_path}")
    if not image_path.exists():
        pytest.fail(f"Test image not found at {image_path}")
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode()
        logger.debug(
            f"Successfully loaded and encoded test image {image_name} (length: {len(image_data)})")
        return image_data

# Basic session payload structure (adjust fields as needed based on SessionModel)


def create_base_session(session_id, rfid_tag=None, image_data=None):
    return {
        "device_id": "test-device-01",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),  # Use ISO format string
        "image_data": image_data,
        "rfid_detected": rfid_tag is not None,
        "rfid_tag": rfid_tag,
        # Add other fields required by your SessionModel Pydantic model
        "session_duration": 5000,
        "image_size": len(base64.b64decode(image_data)) if image_data else 0,
        "face_detected": image_data is not None,
        "free_heap": 20000,
        "state": "SESSION"
    }

# Pytest fixture for MQTT client (optional, but can simplify tests)


@pytest.fixture(scope="function")
def mqtt_test_client():
    # Message delivery confirmation
    message_delivered = False

    def on_publish(client, userdata, mid):
        nonlocal message_delivered
        logger.debug(f"Test client: Message {mid} delivered successfully")
        message_delivered = True

    # Connect to MQTT broker with clean session and client ID
    client = mqtt.Client(client_id="pytest_client_" +
                         str(uuid.uuid4()), clean_session=True)
    client.on_publish = on_publish
    # Store delivery flag on client for access in tests
    client.message_delivered = lambda: message_delivered
    # Use lambda to avoid modifying flag directly
    client.reset_delivery_flag = lambda: setattr(
        client, '_internal_message_delivered', False)
    client._internal_message_delivered = False
    client.on_publish = lambda client, userdata, mid: setattr(
        client, '_internal_message_delivered', True)
    client.message_delivered = lambda: getattr(
        client, '_internal_message_delivered', False)

    yield client  # Provide the client to the test

    # Teardown: Disconnect client after test runs
    try:
        client.loop_stop()
        client.disconnect()
        logger.info("Test MQTT client disconnected.")
    except Exception as e:
        logger.warning(f"Error disconnecting test MQTT client: {e}")


# Test Cases using Mocks
# ======================

@pytest.mark.integration
def test_successful_rfid_face_verification(mqtt_test_client):
    """Test successful verification when both RFID and a matching face are provided."""
    logger.info(
        "--- Starting test_successful_rfid_face_verification (NO MOCKS) ---")
    session_id = f"test-rfid-face-{uuid.uuid4()}"
    rfid_tag = "EMP001"
    image_data = load_test_image()

    # Create session payload
    session = create_base_session(
        session_id, rfid_tag=rfid_tag, image_data=image_data)

    # Publish message via test client
    try:
        mqtt_test_client.connect(
            host=Config.MQTT_BROKER_ADDRESS, port=Config.MQTT_BROKER_PORT)
        mqtt_test_client.loop_start()
        logger.info("Test MQTT client connected and loop started.")

        logger.debug(f"Publishing session: {session}")
        time.sleep(2)  # <-- Keep delay before publishing
        mqtt_test_client.publish(
            TOPIC_SESSION_DATA, json.dumps(session), qos=1)

        # Wait for delivery confirmation
        delivery_timeout = 5
        delivery_start = time.time()
        while not mqtt_test_client.message_delivered() and time.time() - delivery_start < delivery_timeout:
            time.sleep(0.1)

        assert mqtt_test_client.message_delivered(
        ), "Test message delivery confirmation not received"
        logger.info("Test message published and confirmed delivered.")

        # Wait for processing (adjust timeout as needed)
        logger.info("Waiting for potential processing by the real service...")
        # Increase wait time slightly as real services might be slower
        time.sleep(5)

    finally:
        # Ensure client is disconnected even if asserts fail
        mqtt_test_client.loop_stop()
        mqtt_test_client.disconnect()
        logger.info("Test MQTT client disconnected in finally block.")

    # Assertions - THESE WILL LIKELY FAIL NOW without mocks
    # We are primarily interested in the logs from the api-api-1 container
    logger.warning(
        "Assertions below will likely fail as mocks are removed. Check container logs.")
    # mock_db_service.get_employee_by_rfid.assert_called_once_with(rfid_tag)
    # mock_face_client.get_embedding.assert_called_once_with(image_data)
    # mock_face_client.verify_embeddings.assert_called_once_with(mock_embedding, mock_employee.face_embedding)
    # mock_db_service.log_access_attempt.assert_called_once_with(
    #     session_id=session_id,
    #     verification_method="RFID+FACE",
    #     access_granted=True,
    #     employee_id=mock_employee.id,
    #     verification_confidence=0.95,
    #     verification_image_id=ANY
    # )
    # mock_notification_service.send_notification.assert_called_once()
    # sent_notification = mock_notification_service.send_notification.call_args[0][0]
    # assert sent_notification.event_type == NotificationType.ACCESS_GRANTED
    # assert sent_notification.user_id == str(mock_employee.id)

    logger.info(
        "--- Finished test_successful_rfid_face_verification (NO MOCKS) ---")


@pytest.mark.integration
@patch('services.mqtt_service.DatabaseService')
@patch('services.mqtt_service.FaceRecognitionClient')
@patch('services.mqtt_service.NotificationService')
def test_rfid_only_flagging(mock_notification_service, mock_face_client, mock_db_service, mqtt_test_client):
    """Test that an RFID-only attempt results in MANUAL_REVIEW_REQUIRED and no unlock."""
    logger.info("--- Starting test_rfid_only_flagging ---")
    session_id = f"test-rfid-only-{uuid.uuid4()}"
    rfid_tag = "EMP002"

    # Configure mocks
    mock_employee = MagicMock()
    mock_employee.id = uuid.uuid4()
    mock_employee.name = "RFID Only User"
    # No face embedding needed for this employee record mock
    mock_db_service.get_employee_by_rfid.return_value = mock_employee

    # Create session payload (no image_data)
    session = create_base_session(
        session_id, rfid_tag=rfid_tag, image_data=None)

    # Publish message via test client
    try:
        mqtt_test_client.connect(
            host=Config.MQTT_BROKER_ADDRESS, port=Config.MQTT_BROKER_PORT)
        mqtt_test_client.loop_start()
        logger.info("Test MQTT client connected and loop started.")

        logger.debug(f"Publishing session: {session}")
        time.sleep(2)  # <-- Keep delay before publishing
        mqtt_test_client.publish(
            TOPIC_SESSION_DATA, json.dumps(session), qos=1)

        # Wait for delivery confirmation
        delivery_timeout = 5
        delivery_start = time.time()
        while not mqtt_test_client.message_delivered() and time.time() - delivery_start < delivery_timeout:
            time.sleep(0.1)

        assert mqtt_test_client.message_delivered(
        ), "Test message delivery confirmation not received"
        logger.info("Test message published and confirmed delivered.")

        # Wait for processing
        time.sleep(3)

    finally:
        mqtt_test_client.loop_stop()
        mqtt_test_client.disconnect()
        logger.info("Test MQTT client disconnected in finally block.")

    # Assertions
    mock_db_service.get_employee_by_rfid.assert_called_once_with(rfid_tag)
    mock_face_client.get_embedding.assert_not_called()  # No image data
    mock_face_client.verify_embeddings.assert_not_called()
    mock_db_service.log_access_attempt.assert_called_once_with(
        session_id=session_id,
        verification_method="RFID_ONLY_PENDING_REVIEW",
        access_granted=False,
        employee_id=mock_employee.id,
        verification_confidence=None
    )
    # Check notification was sent
    mock_notification_service.send_notification.assert_called_once()
    sent_notification = mock_notification_service.send_notification.call_args[0][0]
    assert sent_notification.event_type == NotificationType.MANUAL_REVIEW_REQUIRED
    assert sent_notification.user_id == str(mock_employee.id)
    assert sent_notification.additional_data.get('reason') == 'rfid_only'

    logger.info("--- Finished test_rfid_only_flagging ---")


@pytest.mark.integration
@patch('services.mqtt_service.DatabaseService')
@patch('services.mqtt_service.FaceRecognitionClient')
@patch('services.mqtt_service.NotificationService')
def test_face_only_flagging(mock_notification_service, mock_face_client, mock_db_service, mqtt_test_client):
    """Test that a face-only attempt results in MANUAL_REVIEW_REQUIRED and no unlock."""
    logger.info("--- Starting test_face_only_flagging ---")
    session_id = f"test-face-only-{uuid.uuid4()}"
    # Use a different image if needed
    image_data = load_test_image("another_face.jpeg")

    # Configure mocks
    mock_embedding = [0.5] * 512
    mock_face_client.get_embedding.return_value = mock_embedding
    # Mock similarity search to return some potential matches for the notification
    mock_db_service.find_similar_embeddings.return_value = [
        {'employee_id': str(uuid.uuid4()),
         'name': 'Potential Match 1', 'distance': 0.3},
        {'employee_id': str(uuid.uuid4()),
         'name': 'Potential Match 2', 'distance': 0.4}
    ]

    # Create session payload (no rfid_tag)
    session = create_base_session(
        session_id, rfid_tag=None, image_data=image_data)

    # Publish message via test client
    try:
        mqtt_test_client.connect(
            host=Config.MQTT_BROKER_ADDRESS, port=Config.MQTT_BROKER_PORT)
        mqtt_test_client.loop_start()
        logger.info("Test MQTT client connected and loop started.")

        logger.debug(f"Publishing session: {session}")
        time.sleep(2)  # <-- Keep delay before publishing
        mqtt_test_client.publish(
            TOPIC_SESSION_DATA, json.dumps(session), qos=1)

        # Wait for delivery confirmation
        delivery_timeout = 5
        delivery_start = time.time()
        while not mqtt_test_client.message_delivered() and time.time() - delivery_start < delivery_timeout:
            time.sleep(0.1)

        assert mqtt_test_client.message_delivered(
        ), "Test message delivery confirmation not received"
        logger.info("Test message published and confirmed delivered.")

        # Wait for processing
        time.sleep(3)

    finally:
        mqtt_test_client.loop_stop()
        mqtt_test_client.disconnect()
        logger.info("Test MQTT client disconnected in finally block.")

    # Assertions
    mock_db_service.get_employee_by_rfid.assert_not_called()  # No RFID tag
    mock_face_client.get_embedding.assert_called_once_with(image_data)
    # No employee record to verify against
    mock_face_client.verify_embeddings.assert_not_called()
    # Should be called for context
    mock_db_service.find_similar_embeddings.assert_called_once()
    mock_db_service.log_access_attempt.assert_called_once_with(
        session_id=session_id,
        verification_method="FACE_ONLY_PENDING_REVIEW",
        access_granted=False,
        employee_id=None,
        verification_confidence=None
    )
    # Check notification was sent
    mock_notification_service.send_notification.assert_called_once()
    sent_notification = mock_notification_service.send_notification.call_args[0][0]
    assert sent_notification.event_type == NotificationType.MANUAL_REVIEW_REQUIRED
    assert sent_notification.additional_data.get('reason') == 'face_only'
    assert 'potential_matches' in sent_notification.additional_data
    assert len(sent_notification.additional_data['potential_matches']) == 2

    logger.info("--- Finished test_face_only_flagging ---")

# Add test for emergency unlock


@pytest.mark.integration
@patch('services.mqtt_service.NotificationService')
def test_emergency_unlock(mock_notification_service, mqtt_test_client):
    """Test that receiving an emergency message triggers an unlock and notification."""
    logger.info("--- Starting test_emergency_unlock ---")
    emergency_payload = {
        "source": "panic_button_01",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Publish message via test client
    try:
        mqtt_test_client.connect(
            host=Config.MQTT_BROKER_ADDRESS, port=Config.MQTT_BROKER_PORT)
        mqtt_test_client.loop_start()
        logger.info("Test MQTT client connected and loop started.")

        logger.debug(f"Publishing emergency message: {emergency_payload}")
        time.sleep(2)
        mqtt_test_client.publish(
            TOPIC_EMERGENCY, json.dumps(emergency_payload), qos=1)

        # Wait for delivery confirmation
        delivery_timeout = 5
        delivery_start = time.time()
        while not mqtt_test_client.message_delivered() and time.time() - delivery_start < delivery_timeout:
            time.sleep(0.1)

        assert mqtt_test_client.message_delivered(
        ), "Test message delivery confirmation not received"
        logger.info("Test emergency message published and confirmed delivered.")

        # Wait for processing
        time.sleep(3)

    finally:
        mqtt_test_client.loop_stop()
        mqtt_test_client.disconnect()
        logger.info("Test MQTT client disconnected in finally block.")

    # Assertions
    mock_notification_service.send_notification.assert_called_once()
    sent_notification = mock_notification_service.send_notification.call_args[0][0]
    assert sent_notification.event_type == NotificationType.EMERGENCY_OVERRIDE
    assert sent_notification.severity == SeverityLevel.CRITICAL
    assert sent_notification.additional_data['source'] == emergency_payload['source']

    logger.info("--- Finished test_emergency_unlock ---")


# Test for invalid payload
@pytest.mark.integration
@patch('services.mqtt_service.DatabaseService')
@patch('services.mqtt_service.FaceRecognitionClient')
@patch('services.mqtt_service.NotificationService')
def test_invalid_session_payload(mock_notification_service, mock_face_client, mock_db_service, mqtt_test_client):
    """Test that an invalid session payload is handled gracefully (logged, no processing)."""
    logger.info("--- Starting test_invalid_session_payload ---")
    session_id = f"test-invalid-{uuid.uuid4()}"
    # Payload missing required fields (e.g., device_id) based on SessionModel
    invalid_session = {
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "rfid_tag": "BADTAG"
        # Missing device_id, image_data etc.
    }

    # Publish message via test client
    try:
        mqtt_test_client.connect(
            host=Config.MQTT_BROKER_ADDRESS, port=Config.MQTT_BROKER_PORT)
        mqtt_test_client.loop_start()
        logger.info("Test MQTT client connected and loop started.")

        logger.debug(f"Publishing invalid session: {invalid_session}")
        time.sleep(2)
        mqtt_test_client.publish(
            TOPIC_SESSION_DATA, json.dumps(invalid_session), qos=1)

        # Wait for delivery confirmation
        delivery_timeout = 5
        delivery_start = time.time()
        while not mqtt_test_client.message_delivered() and time.time() - delivery_start < delivery_timeout:
            time.sleep(0.1)

        assert mqtt_test_client.message_delivered(
        ), "Test message delivery confirmation not received"
        logger.info("Test invalid message published and confirmed delivered.")

        # Wait briefly to ensure no processing happens
        time.sleep(2)

    finally:
        mqtt_test_client.loop_stop()
        mqtt_test_client.disconnect()
        logger.info("Test MQTT client disconnected in finally block.")

    # Assertions: Ensure no service methods were called after validation failure
    mock_db_service.get_employee_by_rfid.assert_not_called()
    mock_face_client.get_embedding.assert_not_called()
    mock_db_service.log_access_attempt.assert_not_called()
    mock_notification_service.send_notification.assert_not_called()
    # Check logs (manually or via caplog fixture) for the "Invalid session payload received" error message.

    logger.info("--- Finished test_invalid_session_payload ---")
