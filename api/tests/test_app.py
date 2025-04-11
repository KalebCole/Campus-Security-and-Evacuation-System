import json
from unittest.mock import Mock


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
