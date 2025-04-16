from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env.development
load_dotenv()


class Config:
    """Application configuration."""
    # Flask config
    DEBUG = os.getenv('DEBUG', 'true').lower() in ["true", "1", "t"]
    SECRET_KEY = os.getenv('SECRET_KEY')

    # Database config
    DATABASE_URL = os.getenv('DATABASE_URL',
                             'postgresql://cses_admin:cses_password_123!@localhost:5432/cses_db')

    # MQTT config
    MQTT_BROKER_ADDRESS = os.getenv('MQTT_BROKER_ADDRESS', 'localhost')
    MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))

    # Face recognition config
    FACE_RECOGNITION_URL = os.getenv(
        'FACE_RECOGNITION_URL', 'http://deepface:5000')

    # Session config
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 30))

    # Face verification threshold
    FACE_VERIFICATION_THRESHOLD = float(
        os.getenv('FACE_VERIFICATION_THRESHOLD', 0.85))

    # Notification Configuration
    ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "False").lower() in [
        "true", "1", "t"]
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    # Expecting comma-separated string in env var, convert to list
    _raw_phone_numbers = os.getenv("NOTIFICATION_PHONE_NUMBERS", "")
    NOTIFICATION_PHONE_NUMBERS = [
        num.strip() for num in _raw_phone_numbers.split(',') if num.strip()]
    # e.g., https://ntfy.sh/your-topic or http://your-server/your-topic
    NTFY_TOPIC = os.getenv("NTFY_TOPIC")

    # Add validation or defaults if necessary
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set.")

    # Add check for SECRET_KEY
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY environment variable not set. Required for sessions and flash messages.")
