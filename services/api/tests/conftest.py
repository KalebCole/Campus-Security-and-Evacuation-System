import pytest
from unittest.mock import Mock, patch
from app import create_app
import os
import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app()
    app.config['TESTING'] = True

    # Ensure face recognition URL is set
    face_recognition_url = os.getenv(
        'FACE_RECOGNITION_URL', 'http://localhost:5001')
    os.environ['FACE_RECOGNITION_URL'] = face_recognition_url
    logger.info(f"Face recognition service URL set to: {face_recognition_url}")

    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def mock_mqtt():
    """Mock MQTT client"""
    with patch('paho.mqtt.client.Client') as mock:
        yield mock
