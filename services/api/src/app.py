import logging
import os
from flask import Flask, jsonify, g, Response
from flask_cors import CORS
from datetime import datetime
from supabase import create_client, Client

from config import Config
from services.database import DatabaseService
from services.face_recognition_client import FaceRecognitionClient
from services.mqtt_service import MQTTService
from services.notification_service import NotificationService
# Import custom filters
from utils.filters import format_verification_method

# Setup logging
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

        # Initialize Supabase Client
        app.supabase_client: Client = create_client(
            app.config.get('SUPABASE_URL'),
            app.config.get('SUPABASE_SERVICE_KEY')
        )
        # Optional: Check if client was created (keys might be missing)
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
    app.emergency_active = False  # Initialize global emergency state

    # --- Register Blueprints ---
    from routes import admin, session, notifications  # Add other blueprints as needed
    app.register_blueprint(admin.admin_bp)

    # --- Register Custom Filters ---
    app.jinja_env.filters['format_verification_method'] = format_verification_method

    # --- Set Content Security Policy ---
    # @app.after_request
    # def add_security_headers(response: Response):
    #     # Allow scripts from self and CDN, allow inline scripts (needed for now)
    #     script_src = "'self' cdn.jsdelivr.net 'unsafe-inline'"
    #     # Allow images from self and Supabase
    #     img_src = "'self' https://icaqsnveqjmzyawjdffw.supabase.co"
    #     # Default to self, allow basic styles/fonts
    #     default_src = "'self'"
    #     style_src = "'self' 'unsafe-inline'" # Allow inline styles if needed by Bootstrap/etc.
    #     font_src = "'self'"
    #
    #     csp_policy = (
    #         f"default-src {default_src}; "
    #         f"script-src {script_src}; "
    #         f"img-src {img_src}; "
    #         f"style-src {style_src}; "
    #         f"font-src {font_src}; "
    #         # Add other directives like connect-src if needed for fetch/XHR later
    #     )
    #     response.headers['Content-Security-Policy'] = csp_policy
    #     # Add other security headers if desired (optional)
    #     # response.headers['X-Content-Type-Options'] = 'nosniff'
    #     # response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    #     # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    #     return response

    logger.info("Flask application created successfully.")
    return app


# Main entry point for running the app directly (e.g., python app.py)
# Gunicorn or other WSGI servers will call create_app() directly.
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=Config.DEBUG)
