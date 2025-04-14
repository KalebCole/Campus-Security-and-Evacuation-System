import logging
import atexit
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from config import Config
from services.database import DatabaseService
from services.face_recognition_client import FaceRecognitionClient
from services.mqtt_service import MQTTService
from services.notification_service import NotificationService
# Import blueprints (assuming you have them)
# from routes.admin import bp as admin_routes
from routes.session import bp as session_routes

# Load environment variables early
load_dotenv('.env.development')

# Basic logging setup
logging.basicConfig(level=logging.INFO if not Config.DEBUG else logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize services


def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Ensure required config is present
    if not Config.DATABASE_URL:
        raise ValueError("DATABASE_URL not set in environment.")
    if not Config.FACE_RECOGNITION_URL:
        logger.warning(
            "FACE_RECOGNITION_URL not set. Face recognition features may fail.")
    if not Config.MQTT_BROKER_ADDRESS:
        logger.warning("MQTT_BROKER_ADDRESS not set. MQTT features may fail.")

    logger.info("Initializing services...")
    try:
        db_service = DatabaseService(Config.DATABASE_URL)
        face_client = FaceRecognitionClient()
        notification_service = NotificationService()
        mqtt_service = MQTTService(
            database_service=db_service,
            face_client=face_client,
            notification_service=notification_service
        )
        mqtt_service.connect()

        # Store services for access in routes if needed (e.g., using app context or blueprints)
        app.db_service = db_service
        app.face_client = face_client
        app.mqtt_service = mqtt_service
        app.notification_service = notification_service

        logger.info("Services initialized.")

    except Exception as e:
        logger.error(
            f"Fatal error during service initialization: {e}", exc_info=True)
        raise  # Re-raise to prevent app from starting in a broken state

    # Register Blueprints (Example)
    # app.register_blueprint(session_routes)
    # app.register_blueprint(admin_routes)

    # Simple root route (health check)
    @app.route('/')
    def health_check():
        # Optionally, add checks for DB, MQTT, Face Client health
        is_mqtt_connected = app.mqtt_service.client.is_connected()
        is_face_healthy = app.face_client.check_health()
        # DB check might involve a simple query
        health_status = {
            "status": "healthy",
            "mqtt_connected": is_mqtt_connected,
            "face_service_healthy": is_face_healthy
        }
        status_code = 200 if is_mqtt_connected and is_face_healthy else 503
        return jsonify(health_status), status_code

    # Register disconnect function to run at exit
    def shutdown_services():
        logger.info("Application shutting down. Disconnecting MQTT client...")
        mqtt_service.disconnect()
    atexit.register(shutdown_services)

    logger.info("Flask application created successfully.")
    return app


# Main entry point for running the app directly (e.g., python app.py)
# Gunicorn or other WSGI servers will call create_app() directly.
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=Config.DEBUG)
