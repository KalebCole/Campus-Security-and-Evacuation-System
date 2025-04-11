from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timezone
import uuid
import requests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='.env.development')
logger.debug(
    f"Face Recognition URL: {os.getenv('FACE_RECOGNITION_URL', 'not set')}")

# In-memory session storage (replace with database in production)
sessions_db = {}
# structure:
# {
#     "session_id": {
#         "face_data": str,
#         "rfid_data": str,
#         "timestamp": str,
#         "status": str,
#         "embedding": list,
#         "is_complete": bool,
#         "error": str
#     }
# }

# used to reduce the number of messages processed
processed_messages = set()  # Track processed message IDs


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize MQTT client
    from paho.mqtt import client as mqtt_client
    client = mqtt_client.Client(client_id="api_service", clean_session=True)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            logger.debug("Subscribing to campus/security/session")
            # Subscribe with QoS 1 for at-least-once delivery
            client.subscribe("campus/security/session", qos=1)
            logger.debug("Subscription complete")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_message(client, userdata, msg):
        try:
            # Generate message ID from payload and topic
            msg_id = f"{msg.topic}:{msg.payload}"

            # Skip if we've already processed this message
            if msg_id in processed_messages:
                logger.debug(f"Skipping duplicate message: {msg_id[:50]}...")
                return

            logger.debug(f"Raw message received on topic {msg.topic}")
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received session: {payload['session_id']}")

            # Log payload without the face data
            debug_payload = payload.copy()
            debug_payload['face_data'] = '<base64_image_data>'
            logger.debug(f"Payload: {debug_payload}")

            # Process session
            process_session(payload)

            # Mark message as processed
            processed_messages.add(msg_id)

            # Limit size of processed_messages set
            if len(processed_messages) > 1000:
                processed_messages.clear()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload received: {e}")
            logger.debug(f"Raw payload that failed: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            logger.exception("Full traceback:")

    def process_session(payload):
        """Process incoming session data"""
        try:
            logger.debug(
                f"Starting to process session {payload.get('session_id', 'unknown')}")

            # Validate required fields
            required_fields = ['session_id',
                               'face_data', 'rfid_data', 'timestamp']
            if not all(field in payload for field in required_fields):
                missing = [f for f in required_fields if f not in payload]
                logger.error(
                    f"Missing required fields in session payload: {missing}")
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
            logger.debug(
                f"Created session record for {session_record['session_id']}")

            # Store session
            sessions_db[session_record['session_id']] = session_record
            logger.debug(
                f"Stored session {session_record['session_id']} in database")

            # Process face recognition
            try:
                face_service_url = os.getenv(
                    'FACE_RECOGNITION_URL', 'http://face_recognition:5001')
                logger.debug(
                    f"Calling face recognition service at {face_service_url}")

                face_payload = {"image": payload['face_data']}
                response = requests.post(
                    f"{face_service_url}/embed", json=face_payload)
                logger.debug(
                    f"Face recognition response status: {response.status_code}")

                if response.status_code == 200:
                    embedding = response.json().get("embedding")
                    session_record["embedding"] = embedding
                    session_record["status"] = "processed"
                    logger.info(
                        f"Successfully processed face for session {session_record['session_id']}")
                    logger.debug(
                        f"Generated embedding of length {len(embedding) if embedding else 0}")
                else:
                    session_record["status"] = "error"
                    session_record[
                        "error"] = f"Face recognition failed with status {response.status_code}"
                    logger.error(f"Face recognition failed: {response.text}")

            except requests.exceptions.RequestException as e:
                session_record["status"] = "error"
                session_record["error"] = str(e)
                logger.error(f"Face recognition request failed: {str(e)}")
                logger.debug(
                    f"Full error details: {type(e).__name__}: {str(e)}")
            except Exception as e:
                session_record["status"] = "error"
                session_record["error"] = str(e)
                logger.error(f"Face recognition error: {str(e)}")
                logger.exception("Full traceback:")

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
            "timestamp": datetime.now(timezone.utc).isoformat()
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
            "timestamp": datetime.now(timezone.utc).isoformat()
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
