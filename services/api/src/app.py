import logging
import os
from flask import Flask, jsonify, g, Response
from flask_cors import CORS
from datetime import datetime
from supabase import create_client, Client

# Updated import path for Config
from src.core.config import Config
# Updated imports for services, routes, utils from src root
from src.services.database import DatabaseService
from src.services.face_recognition_client import FaceRecognitionClient
from src.services.mqtt_service import MQTTService
from src.services.notification_service import NotificationService
from src.utils.filters import format_verification_method

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(Config)
    CORS(app)

    # --- Service Initialization ---
    logger.info("Initializing services...")
    try:
        app.db_service = DatabaseService(app.config['DATABASE_URL'])
        app.face_client = FaceRecognitionClient()
        app.notification_service = NotificationService()
        app.mqtt_service = MQTTService(
            app, app.db_service, app.face_client, app.notification_service)
        app.mqtt_service.connect()

        app.supabase_client: Client = create_client(
            app.config.get('SUPABASE_URL'),
            app.config.get('SUPABASE_SERVICE_KEY')
        )

        if not app.config.get('SUPABASE_URL') or not app.config.get('SUPABASE_SERVICE_KEY'):
            logger.warning(
                "Supabase client initialized WITHOUT URL or Key. Check .env configuration.")
        else:
            logger.info("Supabase client initialized successfully.")

        logger.info("Services initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise

    # --- Global State --- (For features like emergency status)
    app.emergency_active = False

    # --- Register Blueprints ---
    from src.routes import admin, session
    app.register_blueprint(admin.admin_bp)

    # --- Register Custom Filters ---
    app.jinja_env.filters['format_verification_method'] = format_verification_method

    logger.info("Flask application created successfully.")
    return app


# Main entry point for running the app directly (e.g., python app.py)
# Gunicorn or other WSGI servers will call create_app() directly.
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=Config.DEBUG)
