import paho.mqtt.client as mqtt
import json
import logging
import uuid
from typing import Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionHandler:
    def __init__(self, broker_address: str = "localhost", broker_port: int = 1883):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Store active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Connect to broker
        logger.info(
            f"Connecting to MQTT broker at {broker_address}:{broker_port}")
        self.client.connect(broker_address, broker_port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to session and status topics
            client.subscribe("campus/security/session")
            client.subscribe("campus/security/status")
            logger.info("Subscribed to session and status topics")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received message on {msg.topic}: {payload}")

            if msg.topic == "campus/security/session":
                self.handle_session_request(payload)
            elif msg.topic == "campus/security/status":
                self.handle_status_check(payload)

        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def handle_session_request(self, payload: Dict[str, Any]):
        """Handle session request from Arduino"""
        device_id = payload.get("device_id")
        if not device_id:
            logger.error("No device_id in session request")
            return

        # Create new session
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "device_id": device_id,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }

        # Send session response
        response = {
            "session_id": session_id,
            "device_id": device_id,
            "status": "active",
            "created_at": self.active_sessions[session_id]["created_at"]
        }

        self.publish_message("campus/security/session/response", response)

    def handle_status_check(self, payload: Dict[str, Any]):
        """Handle status check from Arduino"""
        device_id = payload.get("device_id")
        if not device_id:
            logger.error("No device_id in status check")
            return

        # Find active session for device
        active_session = None
        for session_id, session in self.active_sessions.items():
            if session["device_id"] == device_id and session["status"] == "active":
                active_session = session_id
                break

        # Send status response
        response = {
            "device_id": device_id,
            "status": "active" if active_session else "inactive",
            "session_id": active_session,
            "timestamp": datetime.now().isoformat()
        }

        self.publish_message("campus/security/status/response", response)

    def publish_message(self, topic: str, payload: Dict[str, Any]):
        """Publish a message to the MQTT broker"""
        try:
            self.client.publish(topic, json.dumps(payload))
            logger.info(f"Published to {topic}: {payload}")
        except Exception as e:
            logger.error(f"Error publishing message: {str(e)}")

    def cleanup(self):
        """Clean up resources"""
        self.client.loop_stop()
        self.client.disconnect()
