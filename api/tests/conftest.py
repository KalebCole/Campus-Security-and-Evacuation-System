import pytest
from unittest.mock import Mock, patch
from app import create_app


@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app()
    app.config['TESTING'] = True
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
