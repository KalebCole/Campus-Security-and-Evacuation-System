import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT Topics
TOPIC_SESSION = "campus/security/session"
TOPIC_SESSION_REQUEST = "campus/security/session/request"
TOPIC_SESSION_STATUS = "campus/security/session/status"


class SessionHandler:
    def __init__(self, broker_address: str = "localhost", broker_port: int = 1883):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Store active sessions: key=device_id, value=session_dict
        self.sessions: Dict[str, Dict[str, Any]] = {}

        self.broker_address = broker_address
        self.broker_port = broker_port

        logger.info(
            f"Initializing Session Handler for {broker_address}:{broker_port}")

    def connect(self):
        try:
            logger.info(
                f"Connecting to MQTT broker at {self.broker_address}:{self.broker_port}")
            self.client.connect(self.broker_address, self.broker_port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {str(e)}")
            raise

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to session-related topics
            client.subscribe(TOPIC_SESSION_REQUEST)
            client.subscribe(TOPIC_SESSION_STATUS)
            logger.info("Subscribed to session topics")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("Unexpected disconnection from MQTT broker")
            # Attempt to reconnect
            self.connect()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received message on {msg.topic}: {payload}")

            if msg.topic == TOPIC_SESSION_REQUEST:
                self._handle_session_request(payload)
            elif msg.topic == TOPIC_SESSION_STATUS:
                self._handle_session_status(payload)

        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def _handle_session_request(self, payload: Dict[str, Any]):
        """Handle session request message"""
        device_id = payload.get("device_id")
        if not device_id:
            logger.error("No device_id in session request")
            return

        # Get or create session
        session = self.sessions.get(device_id)
        if not session:
            logger.info(f"No active session found for device {device_id}")
            self._publish_session_status(device_id, "not_found")
            return

        # Publish current session status
        self._publish_session_status(device_id, "active", session)

    def _handle_session_status(self, payload: Dict[str, Any]):
        """Handle session status message"""
        device_id = payload.get("device_id")
        status = payload.get("status")

        if not device_id or not status:
            logger.error(
                "Missing device_id or status in session status message")
            return

        logger.info(
            f"Received session status update for device {device_id}: {status}")

    def _publish_session_status(self, device_id: str, status: str, session_data: Dict[str, Any] = None):
        """Publish session status to MQTT"""
        try:
            payload = {
                "device_id": device_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }

            if session_data:
                payload.update(session_data)

            self.client.publish(TOPIC_SESSION_STATUS, json.dumps(payload))
            logger.info(f"Published session status: {payload}")
        except Exception as e:
            logger.error(f"Failed to publish session status: {str(e)}")

    def update_session(self, device_id: str, session_data: Dict[str, Any]):
        """Update session data"""
        self.sessions[device_id] = session_data
        logger.info(f"Updated session for device {device_id}")

    def get_session(self, device_id: str) -> Dict[str, Any]:
        """Get session data"""
        return self.sessions.get(device_id)

    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
