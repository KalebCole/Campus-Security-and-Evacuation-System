import pytest
from app import app as flask_app
from config import Config
import uuid


@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client


def test_config_loading():
    """Test that config values are loaded correctly."""
    assert Config.DATABASE_URL is not None
    assert Config.SESSION_TIMEOUT == 30
    assert Config.DEBUG is True


def test_session_lifecycle(client):
    """Test basic session operations."""
    # Create test session data
    session_id = str(uuid.uuid4())
    session_data = {
        "device_id": "test-device",
        "session_id": session_id,
        "timestamp": 1234567890,
        "session_duration": 0,
        "image_size": 1024,
        "image_data": "SGVsbG8gV29ybGQ=",
        "rfid_detected": False,
        "face_detected": False,
        "free_heap": 50000,
        "state": "FACE_DETECTING"
    }

    # Test session creation
    response = client.post(
        '/api/sessions/update',
        json=session_data
    )
    assert response.status_code == 200

    # Test getting session
    response = client.get(f'/api/sessions/{session_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['state'] == 'FACE_DETECTING'

    # Test updating session
    session_data['state'] = 'SESSION'
    session_data['face_detected'] = True
    response = client.post(
        '/api/sessions/update',
        json=session_data
    )
    assert response.status_code == 200

    # Verify update
    response = client.get(f'/api/sessions/{session_id}')
    data = response.get_json()
    assert data['state'] == 'SESSION'
    assert data['face_detected'] is True
