"""
Face recognition service main application.
"""

import os
from flask import Flask
from service.routes import face_recognition_routes


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(face_recognition_routes)

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
