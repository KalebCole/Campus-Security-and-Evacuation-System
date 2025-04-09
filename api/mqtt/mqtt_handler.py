import paho.mqtt.client as mqtt
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT Topics
TOPIC_FACE = "campus/security/face"
TOPIC_RFID = "campus/security/rfid"
TOPIC_SESSION = "campus/security/session"
TOPIC_ACTIVATE = "campus/security/activate"
TOPIC_EMERGENCY = "campus/security/emergency/+"


class MQTTHandler:
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
            f"Initializing MQTT Handler for {broker_address}:{broker_port}")

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
            # Subscribe to all required topics
            client.subscribe(TOPIC_FACE)
            client.subscribe(TOPIC_RFID)
            client.subscribe(TOPIC_SESSION)
            client.subscribe(TOPIC_ACTIVATE)
            client.subscribe(TOPIC_EMERGENCY)
            logger.info("Subscribed to all required topics")
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

            if msg.topic == TOPIC_FACE:
                self._handle_face(payload)
            elif msg.topic == TOPIC_RFID:
                self._handle_rfid(payload)
            elif msg.topic == TOPIC_ACTIVATE:
                self._handle_activate(payload)
            elif msg.topic.startswith("campus/security/emergency/"):
                self._handle_emergency(payload, msg.topic)

        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def _get_or_create_session(self, device_id: str) -> Dict[str, Any]:
        """Get existing session or create a new one"""
        if device_id not in self.sessions:
            self.sessions[device_id] = {
                "session_id": str(uuid.uuid4()),
                "device_id": device_id,
                "status": "active",
                "rfid_verified": False,
                "face_verified": False,
                "created_at": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat()
            }
            logger.info(f"Created new session for device {device_id}")

        return self.sessions[device_id]

    def _publish_session(self, session_data: Dict[str, Any]):
        """Publish session update to MQTT"""
        try:
            self.client.publish(TOPIC_SESSION, json.dumps(session_data))
            logger.info(f"Published session update: {session_data}")
        except Exception as e:
            logger.error(f"Failed to publish session update: {str(e)}")

    def _handle_face(self, payload: Dict[str, Any]):
        """Handle face detection message"""
        device_id = payload.get("device_id")
        if not device_id:
            logger.error("No device_id in face message")
            return

        session = self._get_or_create_session(device_id)
        session["face_verified"] = True
        session["timestamp"] = datetime.now().isoformat()
        self._publish_session(session)

    def _handle_rfid(self, payload: Dict[str, Any]):
        """Handle RFID message"""
        device_id = payload.get("device_id")
        if not device_id:
            logger.error("No device_id in RFID message")
            return

        session = self._get_or_create_session(device_id)
        session["rfid_verified"] = True
        session["timestamp"] = datetime.now().isoformat()
        self._publish_session(session)

    def _handle_activate(self, payload: Dict[str, Any]):
        """Handle system activation message"""
        device_id = payload.get("device_id")
        if not device_id:
            logger.error("No device_id in activation message")
            return

        logger.info(f"System activated by device {device_id}")

    def _handle_emergency(self, payload: Dict[str, Any], topic: str):
        """Handle emergency message"""
        logger.info(f"Emergency detected: {payload}")

    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
