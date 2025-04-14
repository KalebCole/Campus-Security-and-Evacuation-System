from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env.development
load_dotenv()


class Config:
    """Application configuration."""
    # Flask config
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

    # Database config
    DATABASE_URL = os.getenv('DATABASE_URL',
                             'postgresql://cses_admin:cses_password_123!@localhost:5432/cses_db')

    # MQTT config
    MQTT_BROKER_ADDRESS = os.getenv('MQTT_BROKER_ADDRESS', 'localhost')
    MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))

    # Face recognition config
    FACE_RECOGNITION_URL = os.getenv(
        'FACE_RECOGNITION_URL', 'http://localhost:5001')

    # Session config
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 30))
