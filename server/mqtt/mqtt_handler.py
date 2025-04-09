import paho.mqtt.client as mqtt
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
import numpy as np  # Keep numpy for find_user stub typing
import requests  # Added for HTTP calls
import os  # Added to get service URL

# Assuming a stub database interface exists
# from server.database_interface import validate_rfid_tag, find_user_by_face_embedding, save_session, get_session
# For now, use dummy functions


def validate_rfid_tag(rfid_tag: str) -> tuple[bool, str | None]:
    logging.info(f"[STUB] Validating RFID: {rfid_tag}")
    # Simulate successful validation for specific tags
    if rfid_tag in ["123456", "654321", "789012"]:
        return True, f"user_{rfid_tag[:3]}"
    return False, None

# Stub expects list or array - adapt if needed


def find_user_by_face_embedding(embedding: Any) -> tuple[bool, str | None]:
    is_valid_embedding = isinstance(
        embedding, (list, np.ndarray)) and len(embedding) > 0
    logging.info(
        f"[STUB] Finding user by face embedding (type: {type(embedding)}, valid: {is_valid_embedding})")
    # Simulate finding a user based on the embedding
    if is_valid_embedding:
        # In real implementation, query pgvector here
        logging.info(
            "[STUB] - Embedding received, simulating successful match.")
        return True, "user_face123"
    logging.warning(
        "[STUB] - Invalid or missing embedding received for lookup.")
    return False, None


def save_session(device_id: str, session_data: Dict):
    logging.info(f"[STUB] Saving session for {device_id}: {session_data}")
    # In-memory implementation is handled within the class
    pass


def get_session(device_id: str) -> Dict | None:
    logging.info(f"[STUB] Getting session for {device_id}")
    # In-memory implementation is handled within the class
    return None


# Configure logging
# TODO: Consider making logging level and format configurable
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MQTT Topics (centralized) - Generally part of the contract, less likely configurable
TOPIC_FACE = "campus/security/face"
TOPIC_RFID = "campus/security/rfid"
TOPIC_SESSION = "campus/security/session"
TOPIC_ACTIVATE = "campus/security/activate"
TOPIC_EMERGENCY = "campus/security/emergency/+"

# TODO: Make session timeout configurable (e.g., via env var)
SESSION_TIMEOUT_SECONDS = 30  # e.g., 30 seconds to get both RFID and face

# --- Configuration ---
# TODO: Move FACE_REC_SERVICE_URL and HTTP_TIMEOUT to a dedicated config module/file
FACE_REC_SERVICE_URL = os.getenv(
    'FACE_REC_SERVICE_URL', 'http://localhost:5001/embed')
# TODO: Make HTTP timeout configurable (e.g., via env var)
HTTP_TIMEOUT = 5  # Timeout for HTTP requests to face service (seconds)


class MQTTHandler:
    # Removed face_embedding_service from constructor
    # TODO: Make broker_address and broker_port configurable (e.g., via env vars/config file)
    def __init__(self, broker_address: str = "localhost", broker_port: int = 1883):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        # Store active sessions: key=device_id, value=session_dict
        self.sessions: Dict[str, Dict[str, Any]] = {}

        self.broker_address = broker_address
        self.broker_port = broker_port
        # Removed self.face_embedding_service

        logger.info(
            f"Initializing MQTT Handler for {broker_address}:{broker_port}")
        logger.info(
            f"Using Face Recognition Service at: {FACE_REC_SERVICE_URL}")

    def connect(self):
        try:
            logger.info(
                f"Connecting to MQTT broker at {self.broker_address}:{self.broker_port}")
            # TODO: MQTT Credentials (username/password) should be configurable if used
            # self.client.username_pw_set(username="user", password="pass")
            # TODO: MQTT TLS settings should be configurable if used
            # self.client.tls_set(ca_certs="ca.crt", certfile="client.crt", keyfile="client.key")
            self.client.connect(self.broker_address, self.broker_port, 60)
            self.client.loop_start()
            logger.info("MQTT client loop started")
        except Exception as e:
            logger.error(
                f"Failed to connect to MQTT broker: {e}", exc_info=True)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected successfully to MQTT broker")
            # Subscribe to relevant topics
            client.subscribe([(TOPIC_FACE, 0),
                              (TOPIC_RFID, 0),
                              (TOPIC_ACTIVATE, 0),
                              (TOPIC_EMERGENCY, 0)])
            logger.info(
                f"Subscribed to: {TOPIC_FACE}, {TOPIC_RFID}, {TOPIC_ACTIVATE}, {TOPIC_EMERGENCY}")
        else:
            logger.error(
                f"Failed to connect to MQTT broker with result code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')
            # Log truncated payload
            logger.info(
                f"Received message on topic '{topic}': {payload_str[:200]}...")
            payload = json.loads(payload_str)

            if topic == TOPIC_RFID:
                self._handle_rfid(payload)
            elif topic == TOPIC_FACE:
                self._handle_face(payload)
            elif topic == TOPIC_ACTIVATE:
                self._handle_activate(payload)
            elif msg.topic.startswith(TOPIC_EMERGENCY.replace('/+', '')):
                # Check if the topic matches the wildcard pattern
                self._handle_emergency(payload, topic)
            else:
                logger.warning(f"Received message on unhandled topic: {topic}")

        except json.JSONDecodeError:
            logger.error(
                f"Invalid JSON payload received on topic {msg.topic}: {msg.payload.decode()}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Error processing message on topic {msg.topic}: {e}", exc_info=True)

    def _get_or_create_session(self, device_id: str) -> Dict[str, Any]:
        now = datetime.now()
        if device_id not in self.sessions or self._is_session_timed_out(self.sessions[device_id]):
            logger.info(f"Creating new session for device_id: {device_id}")
            self.sessions[device_id] = {
                "session_id": str(uuid.uuid4()),
                "device_id": device_id,
                "auth_status": "partial",
                "rfid_verified": False,
                "face_verified": False,
                "rfid_user": None,
                "face_user": None,
                "created_at": now,
                "last_updated_at": now,
                "access_granted": False,  # Default to no access
                "user_id": None  # Final matched user ID
            }
        else:
            # Update timestamp for existing session
            self.sessions[device_id]["last_updated_at"] = now
        return self.sessions[device_id]

    def _is_session_timed_out(self, session: Dict[str, Any]) -> bool:
        now = datetime.now()
        last_update = session.get("last_updated_at", session["created_at"])
        if now - last_update > timedelta(seconds=SESSION_TIMEOUT_SECONDS):
            logger.warning(
                f"Session {session['session_id']} for device {session['device_id']} timed out.")
            return True
        return False

    def _handle_rfid(self, payload: Dict[str, Any]):
        device_id = payload.get("device_id")
        rfid_tag = payload.get("rfid_tag")

        if not device_id or not rfid_tag:
            logger.error(
                f"Missing device_id or rfid_tag in RFID payload: {payload}")
            return

        session = self._get_or_create_session(device_id)
        if session["auth_status"] == "complete":
            logger.info(
                f"Ignoring RFID for already completed session {session['session_id']}")
            return  # Or start a new session? For now, ignore.

        is_valid, user_id = validate_rfid_tag(rfid_tag)
        session["rfid_verified"] = is_valid
        session["rfid_user"] = user_id if is_valid else None
        logger.info(
            f"RFID validation result for session {session['session_id']}: {is_valid}, user: {user_id}")

        self._check_and_complete_session(session)
        self._publish_session(session)

    # Rewritten _handle_face to call Face Rec Service
    def _handle_face(self, payload: Dict[str, Any]):
        device_id = payload.get("device_id")
        image_b64 = payload.get("image")  # Base64 encoded string

        if not device_id or not image_b64:
            logger.error(
                f"Missing device_id or image in face payload: {payload}")
            return

        session = self._get_or_create_session(device_id)
        if session["auth_status"] == "complete":
            logger.info(
                f"Ignoring Face for already completed session {session['session_id']}")
            return

        embedding = None
        try:
            logger.info(
                f"Sending image to Face Rec Service at {FACE_REC_SERVICE_URL} for session {session['session_id']}")
            # 1. Call the Face Recognition service /embed endpoint
            response = requests.post(
                FACE_REC_SERVICE_URL,
                json={"image": image_b64},
                timeout=HTTP_TIMEOUT
            )
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()

            # 2. Get embedding from response
            response_data = response.json()
            embedding = response_data.get("embedding")  # This should be a list

            if embedding:
                logger.info(
                    f"Successfully received embedding from service for session {session['session_id']}. Embedding length: {len(embedding)}")
                # 3. Use the embedding for lookup (find_user_by_face_embedding is still a stub)
                is_match, user_id = find_user_by_face_embedding(embedding)
                session["face_verified"] = is_match
                session["face_user"] = user_id if is_match else None
                logger.info(
                    f"Face validation result for session {session['session_id']}: {is_match}, user: {user_id}")
            else:
                logger.error(
                    f"Face Rec Service did not return an embedding for session {session['session_id']}. Response: {response_data}")
                session["face_verified"] = False
                session["face_user"] = None

        except requests.exceptions.RequestException as e:
            logger.error(
                f"HTTP request to Face Rec Service failed for session {session['session_id']}: {e}", exc_info=True)
            # Mark as failed on connection error/timeout
            session["face_verified"] = False
            session["face_user"] = None
        except Exception as e:
            # Catch other potential errors like JSON decoding of the response
            logger.error(
                f"Error during face processing via service for session {session['session_id']}: {e}", exc_info=True)
            session["face_verified"] = False
            session["face_user"] = None

        # Proceed to check session completion and publish status regardless of processing success/failure
        self._check_and_complete_session(session)
        self._publish_session(session)

    def _check_and_complete_session(self, session: Dict[str, Any]):
        if session["rfid_verified"] and session["face_verified"]:
            logger.info(
                f"Both RFID and Face verified for session {session['session_id']}")
            # Basic check: do the identified users match?
            if session["rfid_user"] is not None and session["face_user"] is not None and session["rfid_user"] == session["face_user"]:
                session["auth_status"] = "complete"
                session["access_granted"] = True
                # Assign the verified user
                session["user_id"] = session["rfid_user"]
                logger.info(
                    f"Session {session['session_id']} completed successfully. Access GRANTED for user {session['user_id']}.")
            else:
                # Session is complete, but failed
                session["auth_status"] = "complete"
                session["access_granted"] = False
                logger.warning(
                    f"Session {session['session_id']} complete but FAILED. RFID user '{session['rfid_user']}' != Face user '{session['face_user']}'. Access DENIED.")
        else:
            # If only one part is verified, status remains 'partial'
            pass

    def _publish_session(self, session_data: Dict[str, Any]):
        # Format the payload according to mqtt.md
        payload = {
            "session_id": session_data["session_id"],
            "device_id": session_data["device_id"],
            "auth_status": session_data["auth_status"],
            "rfid_verified": session_data["rfid_verified"],
            "face_verified": session_data["face_verified"],
            # Ensure it exists
            "access_granted": session_data.get("access_granted", False),
            "user_id": session_data.get("user_id"),  # Include if available
            "timestamp": datetime.now().isoformat()  # Use current time for publish event
        }
        try:
            # Use default=str for datetime obj
            payload_json = json.dumps(payload, default=str)
            self.client.publish(TOPIC_SESSION, payload_json)
            logger.info(
                f"Published session update to {TOPIC_SESSION}: {payload_json}")
        except Exception as e:
            logger.error(
                f"Error publishing session message: {e}", exc_info=True)

    def _handle_activate(self, payload: Dict[str, Any]):
        # Task 1.2: Stub implementation
        device_id = payload.get("device_id")
        active = payload.get("active", False)
        logger.info(
            f"[STUB] Received activation from {device_id}. Active: {active}")
        # Potential future: Update internal system state

    def _handle_emergency(self, payload: Dict[str, Any], topic: str):
        # Task 1.2: Stub implementation
        source = payload.get("source", "unknown")
        emergency_status = payload.get("emergency", False)
        logger.info(
            f"[STUB] Received emergency signal on {topic}. Source: {source}, Emergency: {emergency_status}")
        # Potential future: Trigger system-wide alert, log event

    def cleanup_sessions(self):
        """Periodically called to remove timed-out sessions"""
        now = datetime.now()
        timed_out_devices = []
        for device_id, session in self.sessions.items():
            last_update = session.get("last_updated_at", session["created_at"])
            if now - last_update > timedelta(seconds=SESSION_TIMEOUT_SECONDS):
                if session["auth_status"] != "complete":  # Only cleanup incomplete sessions
                    logger.warning(
                        f"Cleaning up timed-out session {session['session_id']} for device {device_id}")
                    timed_out_devices.append(device_id)

        for device_id in timed_out_devices:
            del self.sessions[device_id]

    def disconnect(self):
        logger.info("Disconnecting MQTT client.")
        self.client.loop_stop()
        self.client.disconnect()


# Example Usage (intended to be integrated into Flask app)
if __name__ == '__main__':
    import time
    import threading
    # Removed FaceEmbedding import and instantiation

    # Use your broker IP if not local
    mqtt_handler = MQTTHandler(broker_address="localhost")
    mqtt_handler.connect()

    # Keep the main thread alive, maybe run session cleanup periodically
    def run_cleanup():
        while True:
            time.sleep(SESSION_TIMEOUT_SECONDS)
            try:
                mqtt_handler.cleanup_sessions()
            except Exception as e:
                logger.error(
                    f"Error during session cleanup: {e}", exc_info=True)

    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        mqtt_handler.disconnect()
        logger.info("Shutdown complete.")
    # Removed FaceEmbedding specific error handling
