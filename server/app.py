from flask import Flask
from app_config import Config
from flask_cors import CORS
import logging
# Import and register routes
from routes import routes_bp
import os
from dotenv import load_dotenv
from mqtt_auth_handler import MQTTAuthHandler

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS
    CORS(app)

    app.register_blueprint(routes_bp, url_prefix='/api')

    # Initialize MQTT authentication handler
    mqtt_handler = MQTTAuthHandler(
        broker_address=os.getenv("MQTT_BROKER", "localhost"),
        broker_port=int(os.getenv("MQTT_PORT", 1883))
    )

    @app.route("/", methods=['GET'])
    def index():
        return "Campus Security System Server"

    @app.route('/api/emergency_stop/<device_id>')
    def emergency_stop_device(device_id):
        mqtt_handler.emergency_stop(device_id)
        return {"status": "success", "message": f"Emergency stop sent to device {device_id}"}

    @app.route('/api/emergency_stop')
    def emergency_stop_all():
        mqtt_handler.emergency_stop()
        return {"status": "success", "message": "Emergency stop sent to all devices"}

    @app.route('/api/device_status/<device_id>')
    def device_status(device_id):
        is_active = mqtt_handler.check_device_status(device_id)
        return {
            "status": "success",
            "device_id": device_id,
            "is_active": is_active
        }

    return app


app = create_app()

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=True, host='0.0.0.0', port=port)
    finally:
        # Clean up MQTT handler when server stops
        mqtt_handler.cleanup()
