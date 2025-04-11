"""Unit tests for the Campus Security Enhancement System API."""

import json
from unittest.mock import Mock
import base64
import time
from pathlib import Path
import paho.mqtt.client as mqtt
import os


def test_index(client):
    """Test index route"""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Campus Security System Server" in response.data


def test_mqtt_message_processing(app, mock_mqtt):
    """Test MQTT message processing"""
    # Create a test message
    test_message = Mock()
    test_message.payload = json.dumps({
        "session_id": "test123",
        "face_data": "test_face_data",
        "rfid_data": "test_rfid",
        "timestamp": "2024-01-01T00:00:00Z"
    }).encode()

    # Get the on_message callback
    on_message = mock_mqtt.return_value.on_message

    # Call on_message with test data
    on_message(None, None, test_message)

    # Verify MQTT publish was called for unlock
    mock_mqtt.return_value.publish.assert_called_once()


def test_emergency_override(client):
    """Test emergency override endpoint"""
    response = client.post('/api/emergency', json={
        "device_id": "test_device"
    })
    assert response.status_code == 200
    assert response.json["status"] == "success"


def test_mqtt_session_with_face_recognition(client):
    """
    Test the full flow of receiving a session via MQTT and processing it with face recognition.

    Requirements:
    - MQTT broker running
    - Face recognition service running
    - Test image in tests/test_images/valid.jpg
    """
    # Load test image
    image_path = Path(__file__).parent / "test_images" / "valid.jpg"
    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode()

    # Create test session
    session = {
        "session_id": "test_session_123",
        "face_data": image_data,
        "rfid_data": "test_rfid_456",
        "timestamp": "2024-03-19T12:00:00Z"
    }

    # Connect to MQTT broker
    mqtt_client = mqtt.Client()
    mqtt_client.connect(
        host=os.getenv('MQTT_BROKER_ADDRESS', 'localhost'),
        port=int(os.getenv('MQTT_BROKER_PORT', 1883))
    )

    # Publish session message
    mqtt_client.publish("campus/security/session", json.dumps(session))
    mqtt_client.disconnect()

    # Wait for processing (adjust timeout as needed)
    max_wait = 5  # seconds
    start_time = time.time()
    processed = False

    while time.time() - start_time < max_wait:
        # Check sessions endpoint
        response = client.get('/api/sessions')
        sessions = response.get_json()

        # Look for our test session
        for sess in sessions:
            if sess['session_id'] == session['session_id']:
                if sess['status'] == 'processed':
                    processed = True
                    test_session = sess
                    break

        if processed:
            break
        time.sleep(0.5)

    assert processed, "Session was not processed within timeout"
    assert test_session['status'] == 'processed'
    assert 'embedding' in test_session
    assert test_session['rfid_data'] == session['rfid_data']
