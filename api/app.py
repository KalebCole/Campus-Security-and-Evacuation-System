from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='.env.development')

# In-memory session storage (replace with database in production)
sessions_db = {}


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

            # Create session record
            session_record = {
                "session_id": payload['session_id'],
                "face_data": payload['face_data'],
                "rfid_data": payload['rfid_data'],
                "is_complete": payload.get('rfid_data') != 'incomplete',
                "timestamp": payload['timestamp'],
                "status": "pending"
            }

            # Store session
            sessions_db[session_record['session_id']] = session_record

            # Process face recognition
            try:
                face_service_url = os.getenv(
                    'FACE_RECOGNITION_URL', 'http://face_recognition:5001')
                face_payload = {"face_data": payload['face_data']}
                response = requests.post(
                    f"{face_service_url}/api/embedding", json=face_payload)

                if response.status_code == 200:
                    embedding = response.json().get("embedding")
                    session_record["embedding"] = embedding
                    session_record["status"] = "processed"
                else:
                    session_record["status"] = "error"
                    session_record["error"] = "Face recognition failed"
            except Exception as e:
                session_record["status"] = "error"
                session_record["error"] = str(e)
                logger.error(f"Face recognition error: {str(e)}")

            # Notify notification service
            try:
                notification_url = os.getenv(
                    'NOTIFICATION_SERVICE_URL', 'http://notification_service:5002')
                notify_payload = {
                    "session_id": session_record['session_id'],
                    "status": session_record["status"]
                }
                requests.post(f"{notification_url}/api/notify",
                              json=notify_payload)
            except Exception as e:
                logger.error(f"Notification error: {str(e)}")

            # Determine if unlock is needed
            if should_unlock(session_record):
                publish_unlock(session_record['session_id'])

        except Exception as e:
            logger.error(f"Error processing session: {str(e)}")

    def should_unlock(session_record):
        """Determine if door should be unlocked based on session data"""
        return session_record.get('is_complete', False) and session_record.get('status') == 'processed'

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
    print(f"Connecting to MQTT broker at {broker}:{port}")
    client.connect(broker, port)
    client.loop_start()

    # Store MQTT client in app context
    app.mqtt_client = client

    @app.route("/", methods=['GET'])
    def index():
        return "Campus Security System Server"

    @app.route('/api/sessions', methods=['GET'])
    def list_sessions():
        """List all sessions (for debugging or frontend display)"""
        return jsonify(list(sessions_db.values()))

    @app.route('/api/emergency', methods=['POST'])
    def emergency_override():
        """Handle emergency override requests"""
        data = request.get_json()
        device_id = data.get('device_id', 'all')

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
            "message": f"Emergency override sent to device {device_id}"
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
