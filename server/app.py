from flask import Flask
from app_config import Config
from flask_cors import CORS
import logging
# Import and register routes
from routes import routes_bp, session_manager
import os
from dotenv import load_dotenv
from mqtt.mqtt_handler import MQTTHandler

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global MQTT handler instance
mqtt_handler = None


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS
    CORS(app)

    app.register_blueprint(routes_bp, url_prefix='/api')

    # Initialize MQTT handler
    global mqtt_handler
    mqtt_handler = MQTTHandler(
        broker_address=os.getenv('MQTT_BROKER_ADDRESS', 'localhost'),
        broker_port=int(os.getenv('MQTT_BROKER_PORT', 1883)),
        session_manager=session_manager
    )

    # Store MQTT handler in app context
    app.mqtt_handler = mqtt_handler

    @app.route("/", methods=['GET'])
    def index():
        return "Campus Security System Server"

    @app.route('/api/emergency_stop/<device_id>')
    def emergency_stop_device(device_id):
        mqtt_handler.publish_message(
            f"campus/security/emergency/{device_id}",
            {"action": "stop"}
        )
        return {"status": "success", "message": f"Emergency stop sent to device {device_id}"}

    @app.route('/api/emergency_stop')
    def emergency_stop_all():
        mqtt_handler.publish_message(
            "campus/security/emergency/all",
            {"action": "stop"}
        )
        return {"status": "success", "message": "Emergency stop sent to all devices"}

    @app.route('/api/device_status/<device_id>')
    def device_status(device_id):
        # Request status from device
        mqtt_handler.publish_message(
            f"campus/security/status/{device_id}",
            {"action": "check_status"}
        )
        return {
            "status": "success",
            "message": "Status check requested"
        }

    return app


app = create_app()

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=True, host='0.0.0.0', port=port)
    finally:
        # Clean up MQTT handler when server stops
        if mqtt_handler:
            mqtt_handler.cleanup()
