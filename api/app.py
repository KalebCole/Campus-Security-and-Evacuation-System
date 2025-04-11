from flask import Flask, jsonify
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize MQTT client
    from paho.mqtt import client as mqtt_client
    client = mqtt_client.Client()

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            # Subscribe to session channel
            client.subscribe("campus/security/session")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received session: {payload}")

            # Process session
            process_session(payload)

        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def process_session(payload):
        """Process incoming session data"""
        try:
            # Validate required fields
            required_fields = ['session_id',
                               'face_data', 'rfid_data', 'timestamp']
            if not all(field in payload for field in required_fields):
                logger.error("Missing required fields in session payload")
                return

            # TODO: Add face recognition processing
            # face_embedding = process_face_data(payload['face_data'])

            # TODO: Add database operations
            # store_session(payload, face_embedding)

            # Determine if unlock is needed
            if should_unlock(payload):
                publish_unlock(payload['session_id'])

        except Exception as e:
            logger.error(f"Error processing session: {str(e)}")

    def should_unlock(payload):
        """Determine if door should be unlocked based on session data"""
        # TODO: Implement proper authentication logic
        # For now, just check if we have both face and RFID data
        return payload.get('rfid_data') != 'incomplete'

    def publish_unlock(session_id):
        """Publish unlock command"""
        unlock_payload = {
            "session_id": session_id,
            "command": "unlock",
            "timestamp": datetime.utcnow().isoformat()
        }
        client.publish(
            "campus/security/unlock",
            json.dumps(unlock_payload)
        )
        logger.info(f"Published unlock command for session {session_id}")

    # Set MQTT callbacks
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to MQTT broker
    broker = os.getenv('MQTT_BROKER_ADDRESS', 'localhost')
    port = int(os.getenv('MQTT_BROKER_PORT', 1883))
    client.connect(broker, port)
    client.loop_start()

    # Store MQTT client in app context
    app.mqtt_client = client

    @app.route("/", methods=['GET'])
    def index():
        return "Campus Security System Server"

    @app.route('/api/emergency_stop/<device_id>')
    def emergency_stop_device(device_id):
        emergency_payload = {
            "session_id": str(uuid.uuid4()),
            "device_id": device_id,
            "action": "stop",
            "timestamp": datetime.utcnow().isoformat()
        }
        client.publish(
            f"campus/security/emergency/{device_id}",
            json.dumps(emergency_payload)
        )
        return jsonify({
            "status": "success",
            "message": f"Emergency stop sent to device {device_id}"
        })

    @app.route('/api/emergency_stop')
    def emergency_stop_all():
        emergency_payload = {
            "session_id": str(uuid.uuid4()),
            "action": "stop",
            "timestamp": datetime.utcnow().isoformat()
        }
        client.publish(
            "campus/security/emergency/all",
            json.dumps(emergency_payload)
        )
        return jsonify({
            "status": "success",
            "message": "Emergency stop sent to all devices"
        })

    @app.route('/api/device_status/<device_id>')
    def device_status(device_id):
        status_payload = {
            "session_id": str(uuid.uuid4()),
            "device_id": device_id,
            "action": "check_status",
            "timestamp": datetime.utcnow().isoformat()
        }
        client.publish(
            f"campus/security/status/{device_id}",
            json.dumps(status_payload)
        )
        return jsonify({
            "status": "success",
            "message": "Status check requested"
        })

    return app


app = create_app()

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 8080))
        app.run(debug=True, host='0.0.0.0', port=port)
    finally:
        # Clean up MQTT client when server stops
        if hasattr(app, 'mqtt_client'):
            app.mqtt_client.loop_stop()
            app.mqtt_client.disconnect()
