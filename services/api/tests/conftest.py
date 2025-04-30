print("testing")
from src.core.config import Config
from src.app import create_app
from unittest.mock import Mock, patch
import pytest
import os
import logging
from dotenv import load_dotenv

# Explicitly load .env from the project root BEFORE other imports
# Assumes conftest.py is in services/api/tests/
# Go up four levels: tests -> api -> services -> Senior Capstone
project_root = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))))
dotenv_path = os.path.join(project_root, '.env')
# Add print for debugging
print(f"Attempting to load .env from: {dotenv_path}")
# Override ensures it loads even if already partially loaded
load_dotenv(dotenv_path=dotenv_path, override=True)

# Check if SECRET_KEY is loaded immediately after
print(
    f"SECRET_KEY in os.environ after load_dotenv: {'SECRET_KEY' in os.environ}")
# Be careful if printing sensitive keys
print(f"Value from os.getenv('SECRET_KEY'): {os.getenv('SECRET_KEY')}")

# Now import modules that might depend on the loaded environment variables


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
