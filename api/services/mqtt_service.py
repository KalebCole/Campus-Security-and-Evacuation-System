"""Handles MQTT communication, message processing, and verification logic."""

import paho.mqtt.client as mqtt
import json
import logging
import base64  # Added for decoding image data
from datetime import datetime  # Added for timestamping unlock message
from typing import Dict, Any, Optional, List  # Added Optional and List
import uuid  # Potentially needed if interacting with UUIDs directly
import socket  # For hostname
import random  # For random suffix
import string  # For random suffix

from config import Config
# Assuming DatabaseService is importable
from services.database import DatabaseService
# Assuming FaceRecognitionClient is importable
# Import error class
from services.face_recognition_client import FaceRecognitionClient, FaceRecognitionClientError
from models.session import Session as SessionModel  # Pydantic model for validation

# Setup logging
logger = logging.getLogger(__name__)

# MQTT Topics (Centralized)
TOPIC_SESSION_DATA = "campus/security/session"
TOPIC_EMERGENCY = "campus/security/emergency"
TOPIC_UNLOCK_COMMAND = "campus/security/unlock"


class MQTTService:
    """Service for handling MQTT connections and processing messages."""

    def __init__(self, database_service: DatabaseService, face_client: FaceRecognitionClient):
        """Initialize the MQTT service with dependencies."""
        self.db_service = database_service
        self.face_client = face_client

        self.broker_address = Config.MQTT_BROKER_ADDRESS
        self.broker_port = Config.MQTT_BROKER_PORT

        # Generate a unique client ID for development server stability
        random_suffix = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=6))
        base_id = f"cses-api-mqtt-{socket.gethostname()}"
        # MQTT client IDs often have length limits, truncate if necessary
        max_len = 23  # Standard MQTT limit, though brokers might allow more
        self.client_id = (base_id[:max_len-7] + '-' + random_suffix) if len(
            base_id) > max_len-7 else base_id + '-' + random_suffix

        logger.info(f"Initializing MQTT client with ID: {self.client_id}")
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        logger.info(
            f"MQTTService initialized for broker {self.broker_address}:{self.broker_port}")

    def connect(self):
        """Connect to the MQTT broker and start the network loop."""
        try:
            logger.info(
                f"Attempting to connect to MQTT broker at {self.broker_address}:{self.broker_port}...")
            self.client.connect(self.broker_address, self.broker_port, 60)
            self.client.loop_start()  # Start background thread for network loop
            logger.info("MQTT client loop started.")
        except Exception as e:
            logger.error(
                f"Failed to connect to MQTT broker: {e}", exc_info=True)
            # Consider retry logic or raising the exception

    def disconnect(self):
        """Disconnect from the MQTT broker gracefully."""
        logger.info("Disconnecting from MQTT broker...")
        self.client.loop_stop()  # Stop the network loop
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker.")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when the client connects to the MQTT broker."""
        if rc == 0:
            logger.info(
                f"Successfully connected to MQTT broker (Return Code: {rc})")
            # Subscribe to topics upon successful connection
            try:
                # Using tuple format for subscribe for potentially better compatibility
                sub_topics = [
                    (TOPIC_SESSION_DATA, 1),  # QoS 1
                    (TOPIC_EMERGENCY, 1)     # QoS 1
                ]
                result, mid = self.client.subscribe(sub_topics)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(
                        f"Successfully subscribed to topics: {sub_topics}")
                else:
                    logger.error(
                        f"Failed to subscribe to topics, result code: {result}")
            except Exception as e:
                logger.error(f"Error during subscription: {e}", exc_info=True)
        else:
            logger.error(
                f"Failed to connect to MQTT broker, return code: {rc}")
            # Consider connection retry logic here

    def _on_disconnect(self, client, userdata, rc):
        """Callback when the client disconnects from the MQTT broker."""
        logger.warning(f"Disconnected from MQTT broker with result code: {rc}")
        if rc != 0:
            logger.error(
                "Unexpected MQTT disconnection. Consider implementing reconnection logic.")
            # TODO: Reconnection logic could be triggered here

    def _on_message(self, client, userdata, msg):
        """Callback when a message is received from the MQTT broker."""
        topic = msg.topic
        payload_str = msg.payload.decode('utf-8')
        logger.info(f"Received message on topic '{topic}'")
        logger.debug(f"Payload: {payload_str}")

        try:
            payload_dict = json.loads(payload_str)

            if topic == TOPIC_SESSION_DATA:
                self._handle_session_message(payload_dict)
            elif topic == TOPIC_EMERGENCY:
                self._handle_emergency_message(payload_dict)
            else:
                logger.warning(f"Received message on unhandled topic: {topic}")

        except json.JSONDecodeError:
            logger.error(
                f"Failed to decode JSON payload from topic '{topic}': {payload_str}")
        except Exception as e:
            logger.error(
                f"Error processing message from topic '{topic}': {e}", exc_info=True)

    def _handle_session_message(self, payload: Dict[str, Any]):
        """Process messages received on the session data topic."""
        logger.info("Handling session message...")
        # 1. Validate payload using Pydantic model
        try:
            session_data = SessionModel(**payload)
            logger.info(
                f"Validated session data for session_id: {session_data.session_id}")
        except Exception as e:  # Catches Pydantic validation errors
            logger.error(f"Invalid session payload received: {e}")
            logger.debug(f"Invalid payload details: {payload}")
            return  # Stop processing if validation fails

        # Initialize verification variables
        new_embedding: Optional[List[float]] = None
        employee_record = None
        verification_result: Optional[Dict[str, Any]] = None
        access_granted: bool = False
        verification_method: str = "NONE"
        confidence: Optional[float] = None
        image_bytes: Optional[bytes] = None
        employee_id_for_log: Optional[uuid.UUID] = None

        try:
            # --- Verification Flow ---
            # 2. Extract Image Data & Get Embedding
            if session_data.image_data:
                try:
                    image_bytes = base64.b64decode(session_data.image_data)
                    logger.debug(
                        f"Decoded image data: {len(image_bytes)} bytes")
                    new_embedding = self.face_client.get_embedding(
                        session_data.image_data)
                    if new_embedding:
                        logger.info(
                            f"Successfully obtained new embedding for session {session_data.session_id}")
                    else:
                        logger.warning(
                            f"Face client returned no embedding for session {session_data.session_id}")
                except FaceRecognitionClientError as face_err:
                    logger.error(
                        f"Face Recognition Client error getting embedding: {face_err}")
                    # Continue without embedding, might still verify via RFID if possible
                except Exception as decode_err:
                    logger.error(
                        f"Error decoding base64 image data: {decode_err}")
                    # Cannot proceed with face verification if image is corrupt
                    image_bytes = None  # Clear potentially corrupt bytes

            # 3. Look up Employee by RFID (if applicable)
            # ASSUMPTION: SessionModel has 'rfid_tag: Optional[str]'
            rfid_tag = getattr(session_data, 'rfid_tag', None)
            if session_data.rfid_detected and rfid_tag:
                logger.info(f"RFID detected, looking up tag: {rfid_tag}")
                employee_record = self.db_service.get_employee_by_rfid(
                    rfid_tag)
                if employee_record:
                    logger.info(
                        f"Found employee {employee_record.name} ({employee_record.id}) for RFID tag {rfid_tag}")
                    employee_id_for_log = employee_record.id
                else:
                    logger.warning(
                        f"RFID tag {rfid_tag} detected but not found in employee database.")
            elif session_data.rfid_detected:
                logger.warning(
                    "rfid_detected is true, but no rfid_tag provided in payload.")

            # 4. Perform Verification Logic
            if employee_record and new_embedding and employee_record.face_embedding:
                # --- RFID + Face Verification ---
                verification_method = "RFID+FACE"
                logger.info(
                    f"Performing RFID+FACE verification for employee {employee_record.id} and session {session_data.session_id}")
                try:
                    verification_result = self.face_client.verify_embeddings(
                        new_embedding, employee_record.face_embedding)
                    if verification_result:
                        confidence = verification_result.get('confidence')
                        # Use confidence threshold from config
                        if verification_result.get('is_match') and confidence >= Config.FACE_VERIFICATION_THRESHOLD:
                            access_granted = True
                            logger.info(
                                f"Verification successful for {employee_record.id}. Confidence: {confidence:.4f}")
                        else:
                            access_granted = False
                            logger.warning(
                                f"Verification failed for {employee_record.id}. Match: {verification_result.get('is_match')}, Confidence: {confidence:.4f} (Threshold: {Config.FACE_VERIFICATION_THRESHOLD})")
                    else:
                        logger.error(
                            "Face client returned no verification result.")
                        access_granted = False  # Treat client error as failure
                except FaceRecognitionClientError as face_err:
                    logger.error(
                        f"Face Recognition Client error during verification: {face_err}")
                    access_granted = False  # Treat client error as failure

            elif new_embedding:
                # --- Face Only Attempt ---
                verification_method = "FACE_ONLY_ATTEMPT"
                access_granted = False  # Face-only access not granted by default in this logic
                logger.warning(
                    f"Face embedding present, but no matching RFID/employee record for session {session_data.session_id}. Access denied.")
                # Optional: Implement find_similar_embeddings here if needed for review purposes
                # potential_matches = self.db_service.find_similar_embeddings(new_embedding)
                # logger.info(f"Potential face matches found: {potential_matches}")

            elif employee_record:
                # --- RFID Only Attempt ---
                verification_method = "RFID_ONLY_ATTEMPT"
                access_granted = False  # RFID-only access not granted by default
                logger.warning(
                    f"RFID match found for {employee_record.id}, but no face embedding provided/obtained for session {session_data.session_id}. Access denied.")
            else:
                # --- Incomplete Data ---
                verification_method = "INCOMPLETE_DATA"
                access_granted = False
                logger.warning(
                    f"Insufficient data for verification for session {session_data.session_id}. Access denied.")

            # 5. Save Verification Image
            if image_bytes:
                saved_image = self.db_service.save_verification_image(
                    session_id=session_data.session_id,
                    image_data=image_bytes,
                    device_id=session_data.device_id,
                    embedding=new_embedding,  # Store the generated embedding
                    matched_employee_id=employee_id_for_log,
                    confidence=confidence,
                    # status='MATCH'/'NO_MATCH'/'PENDING' # If you add verification_status column
                    processed=True  # Mark as processed by this handler
                )
                if not saved_image:
                    logger.error(
                        f"Failed to save verification image for session {session_data.session_id}")
                # else: Use saved_image.id if linking access_log to verification_image

            # 6. Log Access Attempt
            log_result = self.db_service.log_access_attempt(
                session_id=session_data.session_id,
                verification_method=verification_method,
                access_granted=access_granted,
                employee_id=employee_id_for_log,
                verification_confidence=confidence
                # verification_image_path=saved_image.id if saved_image else None # Example if linking tables
            )
            if not log_result:
                logger.error(
                    f"Failed to log access attempt for session {session_data.session_id}")

            # 7. Publish Unlock if Granted
            if access_granted:
                self._publish_unlock(session_data.session_id)

            # 8. Update SessionRecord (Optional - depends if state needs changing here)
            # self.db_service.update_session(session_id=uuid.UUID(session_data.session_id), state="VERIFIED" or "FAILED")

        except Exception as main_err:
            # Catch-all for unexpected errors during the flow
            logger.error(
                f"Unexpected error during session processing for {session_data.session_id}: {main_err}", exc_info=True)
            # Log a failed access attempt if an unexpected error occurs
            try:
                self.db_service.log_access_attempt(
                    session_id=session_data.session_id,
                    verification_method="SYSTEM_ERROR",
                    access_granted=False
                )
            except Exception as log_err:
                logger.error(
                    f"Failed even to log the system error access attempt: {log_err}")

    def _handle_emergency_message(self, payload: Dict[str, Any]):
        """Process messages received on the emergency topic."""
        logger.warning(
            # Log as warning for visibility
            f"Emergency message received: {payload}")
        source = payload.get("source", "unknown")
        timestamp = payload.get("timestamp", "missing")
        logger.info(f"Emergency triggered by {source} at {timestamp}")
        # TODO: Log emergency event to database?
        # Publish unlock command immediately
        # Use a specific identifier for emergency unlocks
        self._publish_unlock(session_id="EMERGENCY")

    def _publish_unlock(self, session_id: str):
        """Publishes an unlock command to the MQTT broker."""
        try:
            unlock_payload = {
                "command": "UNLOCK",
                "session_id": session_id,  # Include session ID for context
                "timestamp": datetime.utcnow().isoformat()
            }
            payload_str = json.dumps(unlock_payload)
            result, mid = self.client.publish(
                TOPIC_UNLOCK_COMMAND, payload=payload_str, qos=1)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(
                    f"Published UNLOCK command for session/event: {session_id}")
            else:
                logger.error(
                    f"Failed to publish UNLOCK command (Result: {result}) for session/event: {session_id}")
        except Exception as e:
            logger.error(
                f"Error publishing unlock command: {e}", exc_info=True)
