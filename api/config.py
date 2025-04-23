import os
from pathlib import Path


class Config:
    """Application configuration."""
    # Flask config
    USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'

    DEBUG = os.environ.get('DEBUG', 'true').lower() in ["true", "1", "t"]
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Database config
    DATABASE_URL = os.environ.get('DATABASE_URL',
                                  'postgresql://cses_admin:cses_password_123!@localhost:5432/cses_db')

    # MQTT config
    MQTT_BROKER_ADDRESS = os.environ.get('MQTT_BROKER_ADDRESS', 'localhost')
    MQTT_BROKER_PORT = int(os.environ.get('MQTT_BROKER_PORT', 1883))

    # Face recognition config
    FACE_RECOGNITION_URL = os.environ.get(
        'FACE_RECOGNITION_URL', 'http://deepface:5000')

    # Session config
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 30))

    # Face verification threshold
    FACE_VERIFICATION_THRESHOLD = float(
        os.environ.get('FACE_VERIFICATION_THRESHOLD', 0.85))

    # Notification Configuration
    ENABLE_NOTIFICATIONS = os.environ.get("ENABLE_NOTIFICATIONS", "False").lower() in [
        "true", "1", "t"]
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
    # Expecting comma-separated string in env var, convert to list
    _raw_phone_numbers = os.environ.get("NOTIFICATION_PHONE_NUMBERS", "")
    NOTIFICATION_PHONE_NUMBERS = [
        num.strip() for num in _raw_phone_numbers.split(',') if num.strip()]
    # e.g., https://ntfy.sh/your-topic or http://your-server/your-topic
    NTFY_TOPIC = os.environ.get("NTFY_TOPIC")

    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    SUPABASE_BUCKET_NAME = os.environ.get(
        'SUPABASE_BUCKET_NAME', 'cses-images')

    # Add validation or defaults if necessary
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set.")

    # Add check for SECRET_KEY
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY environment variable not set. Required for sessions and flash messages.")

    # Check Supabase config (optional, but recommended)
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables not set. Storage operations will fail.")
