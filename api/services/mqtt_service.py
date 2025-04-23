import paho.mqtt.client as mqtt  # Correct import
import json
import logging  # Correct import
import base64
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import socket
import random
import string
import sqlalchemy.exc  # Add import for SQLAlchemy exceptions

from config import Config  # Import Config
from services.database import DatabaseService  # Correct import path
# Import error class
from services.face_recognition_client import FaceRecognitionClient, FaceRecognitionClientError
from models.session import Session as SessionModel  # Correct import path
# Correct import path and content
from models.notification import Notification, NotificationType, SeverityLevel
from services.notification_service import NotificationService  # Correct import path
from services.storage_service import upload_image_to_supabase  # Import the new function

# Setup logging
logger = logging.getLogger(__name__)  # Initialize logger correctly

# --- Import global state ---
# Removed direct import - state will be accessed via self.app
# --- End Import global state ---

# MQTT Topics (Centralized)
TOPIC_SESSION_DATA = "campus/security/session"
TOPIC_EMERGENCY = "campus/security/emergency"
TOPIC_UNLOCK_COMMAND = "campus/security/unlock"


class MQTTService:
    """Service for handling MQTT connections and processing messages."""

    def __init__(self, app, database_service: DatabaseService, face_client: FaceRecognitionClient, notification_service: NotificationService):
        """Initialize the MQTT service with dependencies and app instance."""
        self.app = app  # Store app instance
        self.db_service = database_service
        self.face_client = face_client
        self.notification_service = notification_service

        self.broker_address = Config.MQTT_BROKER_ADDRESS
        self.broker_port = Config.MQTT_BROKER_PORT

        # Generate a unique client ID
        random_suffix = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=6))
        base_id = f"cses-api-mqtt-{socket.gethostname()}"
        max_len = 23
        self.client_id = (base_id[:max_len-7] + '-' + random_suffix) if len(
            base_id) > max_len-7 else base_id + '-' + random_suffix

        logger.info(f"Initializing MQTT client with ID: {self.client_id}")
        # Initialize the client correctly
        self.client = mqtt.Client(
            client_id=self.client_id, protocol=mqtt.MQTTv311)
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
            self.client.loop_start()
            logger.info("MQTT client loop started.")
        except Exception as e:
            logger.error(
                f"Failed to connect to MQTT broker: {e}", exc_info=True)

    def disconnect(self):
        """Disconnect from the MQTT broker gracefully."""
        logger.info("Disconnecting from MQTT broker...")
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker.")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when the client connects to the MQTT broker."""
        if rc == 0:
            logger.info(
                f"Successfully connected to MQTT broker (Return Code: {rc})")
            try:
                sub_topics = [
                    (TOPIC_SESSION_DATA, 1),
                    (TOPIC_EMERGENCY, 1)
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

    def _on_disconnect(self, client, userdata, rc):
        """Callback when the client disconnects from the MQTT broker."""
        logger.warning(f"Disconnected from MQTT broker with result code: {rc}")
        if rc != 0:
            logger.error(
                "Unexpected MQTT disconnection. Reconnection logic needed.")

    # Restore original _on_message structure (keeping added logs)
    def _on_message(self, client, userdata, msg):
        """Callback when a message is received from the MQTT broker."""
        topic = msg.topic
        payload_str = msg.payload.decode('utf-8')
        logger.info(f"Received message on topic '{topic}'")
        logger.debug(f"Raw Payload: {payload_str}")  # Keep this log

        try:
            logger.debug("Attempting JSON decode...")  # Keep this log
            payload_dict = json.loads(payload_str)
            logger.debug("JSON decoded successfully.")  # Keep this log

            if topic == TOPIC_SESSION_DATA:
                # Keep this log
                logger.debug("Routing to _handle_session_message...")
                self._handle_session_message(payload_dict)
            elif topic == TOPIC_EMERGENCY:
                # Keep this log
                logger.debug("Routing to _handle_emergency_message...")
                self._handle_emergency_message(payload_dict)
            else:
                logger.warning(f"Received message on unhandled topic: {topic}")

        except json.JSONDecodeError:
            # Add exc_info
            logger.error(
                f"Failed to decode JSON payload from topic '{topic}': {payload_str}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Error processing message from topic '{topic}': {e}", exc_info=True)

    # Restore original _handle_session_message structure (keeping added logs)
    def _handle_session_message(self, payload: Dict[str, Any]):
        """Process messages received on the session data topic."""
        logger.info("Handling session message...")
        # Keep this log
        logger.debug(f"Session payload dict received: {payload}")

        # --- Early Exit for Duplicate Session ID Processing ---
        temp_session_id = payload.get('session_id')
        if temp_session_id:
            try:
                existing_log = self.db_service.get_access_log_by_session_id(
                    temp_session_id)
                if existing_log:
                    logger.warning(
                        f"Duplicate message received for already processed session_id: {temp_session_id}. Skipping further processing.")
                    return  # Exit early
                else:
                    logger.debug(
                        f"Session ID {temp_session_id} is new. Proceeding with processing.")
            except Exception as check_err:
                # Log error but maybe proceed cautiously?
                logger.error(
                    f"Error checking for existing session log {temp_session_id}: {check_err}", exc_info=True)
                # Depending on policy, might want to return here or continue.
                # For now, let's proceed but the error is logged.
        else:
            logger.warning(
                "Received session message without a session_id in payload. Cannot check for duplicates.")
            # Might want to return here as session_id is crucial
            # return
        # ------------------------------------------------------

        # 1. Validate payload
        try:
            logger.debug("Attempting Pydantic validation...")  # Keep this log
            session_data = SessionModel(**payload)
            logger.info(
                f"Validated session data for session_id: {session_data.session_id}")
            # Keep this log
            logger.debug(f"Validated SessionModel: {session_data.dict()}")
        except Exception as e:  # Catches Pydantic validation errors
            logger.error(
                f"Invalid session payload received: {e}", exc_info=True)
            logger.debug(f"Invalid payload details: {payload}")
            return

        # Initialize verification variables
        new_embedding: Optional[List[float]] = None
        employee_record = None
        verification_result: Optional[Dict[str, Any]] = None
        access_granted: bool = False
        verification_method: str = "NONE"
        confidence: Optional[float] = None
        image_bytes: Optional[bytes] = None
        employee_id_for_log: Optional[uuid.UUID] = None
        notification_to_send: Optional[Notification] = None
        storage_url: Optional[str] = None  # Added to store Supabase URL
        logger.debug("Initialized verification variables.")  # Keep this log

        try:
            # --- Verification Flow ---
            # 2. Extract Image Data & Get Embedding (if face detected)
            logger.debug(
                f"Checking for image. Present: {session_data.image is not None}")
            if session_data.image:
                try:
                    image_bytes = base64.b64decode(session_data.image)
                    logger.debug(
                        f"Decoded image data: {len(image_bytes)} bytes")

                    # --- Upload Image to Supabase FIRST ---
                    # Generate a unique filename including the folder path
                    image_filename = f"verification_images/session_{session_data.session_id}.jpg"
                    logger.info(
                        f"Attempting to upload {image_filename} to Supabase Storage.")
                    storage_url = upload_image_to_supabase(
                        image_bytes, image_filename)
                    if storage_url:
                        logger.info(
                            f"Image uploaded successfully. URL: {storage_url}")
                    else:
                        logger.error(
                            f"Failed to upload image {image_filename} to Supabase Storage.")
                        # Decide how to proceed - maybe log error but continue without image?
                        # For now, we log the error and storage_url remains None
                    # ------------------------------------

                    # --- Only get embedding if face was detected by ESP32 ---
                    if session_data.face_detected:
                        logger.debug(
                            f"face_detected is True. Calling face_client.get_embedding for session {session_data.session_id}")
                        new_embedding = self.face_client.get_embedding(
                            session_data.image)
                        if new_embedding:
                            logger.info(
                                f"Successfully obtained new embedding for session {session_data.session_id}")
                            logger.debug(
                                f"Embedding received (first 10 values): {new_embedding[:10]}...")
                        else:
                            # This case might indicate an issue with the face service if face_detected was true
                            logger.warning(
                                f"Face client returned no embedding despite face_detected=True for session {session_data.session_id}")
                            # notification_to_send = Notification(
                            #     event_type=NotificationType.SYSTEM_ERROR,  # Potentially SYSTEM_ERROR
                            #     severity=SeverityLevel.WARNING,
                            #     session_id=session_data.session_id,
                            #     message="Face embedding could not be generated, despite face detected flag being true."
                            # )
                    else:
                        # If face_detected is false, skip embedding call
                        logger.info(
                            f"face_detected is False. Skipping face embedding generation for session {session_data.session_id}.")
                        new_embedding = None  # Ensure embedding is None

                except FaceRecognitionClientError as face_err:
                    # Handle potential errors even if skipped above (though less likely)
                    logger.error(
                        f"Face Recognition Client error getting embedding: {face_err}", exc_info=True)
                    notification_to_send = Notification(
                        event_type=NotificationType.SYSTEM_ERROR,
                        severity=SeverityLevel.WARNING,
                        session_id=session_data.session_id,
                        message=f"Face recognition service error during embedding: {face_err}"
                    )
                except Exception as decode_or_upload_err:
                    logger.error(
                        f"Error decoding/uploading image data: {decode_or_upload_err}", exc_info=True)
                    image_bytes = None  # Ensure bytes are None if decode/upload fails
                    new_embedding = None
                    storage_url = None  # Ensure URL is None
                    notification_to_send = Notification(
                        event_type=NotificationType.SYSTEM_ERROR,
                        severity=SeverityLevel.WARNING,
                        session_id=session_data.session_id,
                        message=f"Failed to decode/upload image data: {decode_or_upload_err}"
                    )
            else:
                # Keep this log
                logger.debug("No image found in payload.")
                image_bytes = None  # Ensure bytes are None
                new_embedding = None
                storage_url = None  # Ensure URL is None

            # 3. Look up Employee by RFID
            rfid_tag = getattr(session_data, 'rfid_tag', None)
            # Keep this log
            logger.debug(
                f"Checking for RFID. rfid_detected={session_data.rfid_detected}, rfid_tag='{rfid_tag}'")
            if session_data.rfid_detected and rfid_tag:
                logger.info(f"RFID detected, looking up tag: {rfid_tag}")
                # Keep this log
                logger.debug(
                    f"Calling db_service.get_employee_by_rfid for tag {rfid_tag}")
                employee_record = self.db_service.get_employee_by_rfid(
                    rfid_tag)
                if employee_record:
                    # Keep this log
                    logger.debug(
                        f"Employee found: {employee_record.id} ({employee_record.name})")
                    employee_id_for_log = employee_record.id
                else:
                    logger.warning(
                        f"RFID tag {rfid_tag} not found in database.")
                    # Trigger RFID_NOT_FOUND notification
                    notification_to_send = Notification(
                        event_type=NotificationType.RFID_NOT_FOUND,
                        severity=SeverityLevel.WARNING,
                        session_id=session_data.session_id,
                        message=f"Unknown RFID tag presented: {rfid_tag}",
                        additional_data={'rfid_tag': rfid_tag}
                    )
                    # Prevent further processing if RFID is unknown
                    # return # Or handle as per specific requirements

            # --- Verification Logic Decision Tree ---
            logger.debug("Entering verification logic decision tree...")
            # Case 1: RFID + Face Detected (and embedding generated)
            # Keep this log
            logger.debug(
                f"Checking Case 1: employee_record? {employee_record is not None}, new_embedding? {new_embedding is not None}, employee_has_embedding? {getattr(employee_record, 'face_embedding', None) is not None}")
            # Explicitly check existence (not truthiness) of embeddings
            if employee_record and new_embedding is not None and employee_record.face_embedding is not None:
                logger.info(
                    f"Performing RFID+Face verification for session {session_data.session_id}")
                try:
                    # NOTE: This now calls the *local* verify_embeddings in the client,
                    # which calculates cosine similarity based on the configured threshold.
                    verification_result = self.face_client.verify_embeddings(
                        new_embedding, employee_record.face_embedding)

                    # Handle potential None return from local verification if inputs were bad
                    if verification_result is None:
                        logger.error(
                            f"Local verification failed for session {session_data.session_id} (likely bad embeddings). Denying access.")
                        access_granted = False
                        verification_method = 'ERROR'
                        confidence = None
                        # Optionally create a system error notification
                        if notification_to_send is None:  # Avoid overwriting previous notifications
                            notification_to_send = Notification(
                                event_type=NotificationType.SYSTEM_ERROR,
                                severity=SeverityLevel.WARNING,
                                session_id=session_data.session_id,
                                message=f"Verification step failed due to invalid embeddings for session {session_data.session_id}."
                            )
                    else:
                        access_granted = verification_result.get(
                            'is_match', False)
                        # Confidence is now the cosine similarity score
                        confidence = verification_result.get('confidence')
                        # Base verification method
                        verification_method = 'RFID+FACE'

                        if access_granted:
                            logger.info(
                                # Log confidence
                                f"RFID+Face verification SUCCESS for session {session_data.session_id}. Confidence: {confidence:.4f}")
                            notification_to_send = Notification(
                                event_type=NotificationType.ACCESS_GRANTED,
                                severity=SeverityLevel.INFO,
                                session_id=session_data.session_id,
                                user_id=str(employee_record.id),
                                message=f"Access granted to {employee_record.name} via RFID+Face.",
                                additional_data={
                                    'employee_name': employee_record.name,
                                    'confidence': confidence
                                }
                            )
                        else:
                            logger.warning(
                                # Log confidence
                                f"RFID+Face verification FAILED for session {session_data.session_id}. Confidence: {confidence:.4f}")
                            # Update verification method if verification failed but embeddings were valid
                            verification_method = 'FACE_VERIFICATION_FAILED'
                            notification_to_send = Notification(
                                event_type=NotificationType.FACE_NOT_RECOGNIZED,  # Or a more specific type?
                                severity=SeverityLevel.WARNING,
                                session_id=session_data.session_id,
                                user_id=str(employee_record.id),
                                message=f"Face verification failed for {employee_record.name} (RFID match). Confidence: {confidence:.2f}. Flagged for review.",
                                additional_data={
                                    'employee_name': employee_record.name,
                                    'confidence': confidence
                                }
                            )

                except FaceRecognitionClientError as face_err:
                    # This handles errors from get_embedding primarily now
                    logger.error(
                        f"Face Recognition Client error during verification flow: {face_err}", exc_info=True)
                    access_granted = False
                    verification_method = 'ERROR'  # Indicate system error
                    notification_to_send = Notification(
                        event_type=NotificationType.SYSTEM_ERROR,
                        severity=SeverityLevel.CRITICAL,
                        session_id=session_data.session_id,
                        message=f"Face recognition client error during verification: {face_err}"
                    )
                # Catch other potential errors during verification logic
                except Exception as verif_err:
                    logger.error(
                        f"Unexpected error during verification block for {session_data.session_id}: {verif_err}", exc_info=True)
                    access_granted = False
                    verification_method = 'ERROR'
                    confidence = None
                    if notification_to_send is None:
                        notification_to_send = Notification(
                            event_type=NotificationType.SYSTEM_ERROR,
                            severity=SeverityLevel.CRITICAL,
                            session_id=session_data.session_id,
                            message=f"Unexpected error during verification: {verif_err}"
                        )

            # Explicitly check if new_embedding exists
            elif new_embedding is not None:
                # --- Face Only Attempt --- Flag for Manual Review ---
                verification_method = "FACE_ONLY_PENDING_REVIEW"
                access_granted = False
                # Keep this log
                logger.warning(
                    f"Entering FACE_ONLY_PENDING_REVIEW branch. Session: {session_data.session_id}")
                # Keep this log
                logger.debug(
                    f"Face embedding present, but no/invalid RFID data. Flagging for manual review. Session: {session_data.session_id}")

                potential_matches_raw = []
                try:
                    # Define context_threshold (adjust as needed, maybe from Config?)
                    context_threshold = Config.FACE_VERIFICATION_THRESHOLD + 0.1
                    # Keep this log
                    logger.debug(
                        f"Calling db_service.find_similar_embeddings for session {session_data.session_id}")
                    potential_matches_raw = self.db_service.find_similar_embeddings(
                        new_embedding, threshold=context_threshold, limit=3)
                    logger.info(
                        f"Potential face matches for review (raw): {potential_matches_raw}")

                    # --- Convert UUIDs to strings for JSON serialization ---
                    potential_matches_serializable = [
                        {
                            # Convert UUID to string
                            "employee_id": str(match['employee_id']),
                            "name": match['name'],
                            "distance": match['distance'],
                            "confidence": match['confidence']
                        } for match in potential_matches_raw
                    ]
                    logger.debug(
                        f"Serializable matches: {potential_matches_serializable}")
                    # -------------------------------------------------------

                except Exception as search_err:
                    logger.error(
                        f"Error during similarity search for Face-Only review context: {search_err}", exc_info=True)
                    potential_matches_serializable = []  # Ensure it's an empty list on error

                notification_to_send = Notification(
                    event_type=NotificationType.MANUAL_REVIEW_REQUIRED,
                    severity=SeverityLevel.INFO,
                    session_id=session_data.session_id,
                    message=f"Face-only access attempt detected. Requires manual review.",
                    additional_data={'reason': 'face_only',
                                     'potential_matches': potential_matches_serializable}  # Use the serializable list
                )

            elif employee_record:
                # --- RFID Only Attempt --- Flag for Manual Review ---
                verification_method = "RFID_ONLY_PENDING_REVIEW"
                access_granted = False
                # Keep this log
                logger.warning(
                    f"Entering RFID_ONLY_PENDING_REVIEW branch. Session: {session_data.session_id}")
                # Keep this log
                logger.debug(
                    f"RFID match found for {employee_record.id}, but no face data. Flagging for manual review. Session: {session_data.session_id}")
                notification_to_send = Notification(
                    event_type=NotificationType.MANUAL_REVIEW_REQUIRED,
                    severity=SeverityLevel.INFO,
                    session_id=session_data.session_id,
                    user_id=str(employee_record.id),
                    message=f"RFID-only access attempt by {employee_record.name}. Requires manual review.",
                    additional_data={'reason': 'rfid_only',
                                     'employee_name': employee_record.name}
                )

            else:
                # --- Incomplete Data ---
                verification_method = "INCOMPLETE_DATA"
                access_granted = False
                # Keep this log
                logger.warning(
                    f"Entering INCOMPLETE_DATA branch. Session: {session_data.session_id}")
                # Keep this log
                logger.debug(
                    f"Insufficient data (no employee record and no new embedding) for verification. Session: {session_data.session_id}. Access denied.")
                if notification_to_send is None:
                    # Keep this log
                    logger.debug(
                        "Creating INCOMPLETE_DATA notification as no prior notification was set.")
                    notification_to_send = Notification(
                        event_type=NotificationType.SYSTEM_ERROR,
                        severity=SeverityLevel.WARNING,
                        session_id=session_data.session_id,
                        message="Incomplete data received for verification (no valid RFID match and no face embedding)."
                    )
                else:
                    # Keep this log
                    logger.debug(
                        "Skipping INCOMPLETE_DATA notification as a prior notification was already set.")

            # 5. Save Verification Image METADATA (URL instead of bytes)
            verification_image_id = None
            logger.debug(
                f"Checking if storage_url exists to save verification metadata. has_storage_url={storage_url is not None}")
            if storage_url:  # Check if upload was successful
                logger.debug(
                    f"Calling db_service.save_verification_image with URL for session {session_data.session_id}")
                saved_image_metadata = self.db_service.save_verification_image(
                    session_id=session_data.session_id,
                    storage_url=storage_url,  # Pass URL instead of image_data
                    device_id=session_data.device_id,
                    embedding=new_embedding,
                    matched_employee_id=employee_id_for_log,
                    confidence=confidence,
                    processed=True
                )
                if not saved_image_metadata:
                    logger.error(
                        f"Failed to save verification image metadata for session {session_data.session_id}")
                else:
                    verification_image_id = saved_image_metadata.id
                    logger.debug(
                        f"Verification image metadata saved with ID: {verification_image_id}")
            else:
                logger.debug(
                    "No storage_url available, skipping verification image metadata save.")

            # 6. Log Access Attempt
            logger.debug("Entering access logging logic.")  # Keep this log
            try:
                # Keep this log
                logger.debug(
                    f"Calling db_service.log_access_attempt for session {session_data.session_id} with method '{verification_method}' and granted={access_granted}")

                # Conditionally set review_status
                review_status_to_log = 'approved' if access_granted else None

                log_result = self.db_service.log_access_attempt(
                    session_id=session_data.session_id,
                    verification_method=verification_method,
                    access_granted=access_granted,
                    employee_id=employee_id_for_log,
                    verification_confidence=confidence,
                    verification_image_id=verification_image_id,
                    # Pass the determined status, or None to let default logic apply
                    review_status=review_status_to_log
                )
                if not log_result:
                    # Clarified error message
                    logger.error(
                        f"Failed to log access attempt for session {session_data.session_id} (db_service returned None).")
                else:
                    # Keep this log
                    logger.debug("Access attempt logged successfully.")
            # Catch specific IntegrityError (covers UniqueViolation)
            except sqlalchemy.exc.IntegrityError as ie:
                # Log as warning, don't need full traceback
                logger.warning(
                    f"Database integrity error logging session {session_data.session_id} - likely duplicate session ID: {ie}", exc_info=False)
            except Exception as log_err:  # Catch other potential logging errors
                logger.error(
                    f"Unexpected error logging access attempt for session {session_data.session_id}: {log_err}", exc_info=True)

            # 7. Publish Unlock if Granted
            # Keep this log
            logger.debug(
                f"Checking if access_granted is True to publish unlock. access_granted={access_granted}")
            if access_granted:
                # Keep this log
                logger.debug(
                    f"Calling _publish_unlock for session {session_data.session_id}")
                self._publish_unlock(session_data.session_id)
            else:
                # Keep this log
                logger.debug("Access not granted, skipping unlock.")

        except Exception as main_err:
            logger.error(
                f"Unexpected error during session processing for {session_data.session_id}: {main_err}", exc_info=True)
            access_granted = False
            # Keep this log
            logger.debug(
                "Logging SYSTEM_ERROR access attempt due to unexpected exception.")
            try:
                self.db_service.log_access_attempt(
                    session_id=session_data.session_id,
                    verification_method="SYSTEM_ERROR",
                    access_granted=False
                )
            except Exception as inner_log_err:
                logger.error(
                    f"Failed even to log the system error access attempt: {inner_log_err}", exc_info=True)

            if notification_to_send is None:
                # Keep this log
                logger.debug(
                    "Creating SYSTEM_ERROR notification due to unexpected exception.")
                notification_to_send = Notification(
                    event_type=NotificationType.SYSTEM_ERROR,
                    severity=SeverityLevel.CRITICAL,
                    session_id=session_data.session_id,
                    message=f"Unexpected error processing session: {main_err}"
                )
            else:
                # Keep this log
                logger.debug(
                    "Skipping SYSTEM_ERROR notification as a prior notification was already set.")

        # 8. Send Notifications (if applicable) - Renumbered from 5
        logger.debug("Entering notification sending logic.")  # Keep this log
        if notification_to_send:
            logger.info(
                f"Notification created: Type={notification_to_send.event_type.name}, Severity={notification_to_send.severity.name}")
            # Changed .dict() to .model_dump() for Pydantic v2
            # Keep this log
            logger.debug(
                f"Notification details before sending: {notification_to_send.model_dump()}")
            self._send_and_log_notification(notification_to_send)
        else:
            # Keep this log
            logger.debug("No notification was generated for this session.")

    # Restore original _handle_emergency_message structure (keeping added logs)
    def _handle_emergency_message(self, payload: Dict[str, Any]):
        """Process messages received on the emergency topic."""
        # global global_emergency_active # REMOVED global keyword
        logger.info("Handling emergency message...")  # Keep this log
        # Keep this log
        logger.debug(f"Raw emergency payload received: {payload}")
        logger.warning(f"EMERGENCY message received: {json.dumps(payload)}")
        source = payload.get("source", "unknown")
        timestamp_str = payload.get("timestamp", datetime.utcnow().isoformat())

        logger.info(
            f"Emergency unlock triggered by {source} at {timestamp_str}")

        # --- Set Global Emergency State ---
        logger.warning("Setting app emergency state to ACTIVE.")
        self.app.emergency_active = True  # Set state on the app instance
        # ---------------------------------

        # Keep this log
        logger.debug("Creating EMERGENCY_OVERRIDE notification.")
        notification = Notification(
            event_type=NotificationType.EMERGENCY_OVERRIDE,
            severity=SeverityLevel.CRITICAL,
            message=f"Emergency unlock triggered by {source}",
            additional_data=payload
        )
        # Keep this log
        logger.debug(
            f"Calling _send_and_log_notification for emergency event (Source: {source}).")
        self._send_and_log_notification(notification)

        # Keep this log
        logger.debug(
            f"Calling _publish_unlock for emergency event (Source: {source}).")
        self._publish_unlock(session_id="EMERGENCY")

    # Restore original _publish_unlock structure (keeping added logs)
    def _publish_unlock(self, session_id: str):
        """Publishes an unlock command to the MQTT broker."""
        logger.debug(
            # Keep this log
            f"Attempting to publish UNLOCK command for session/event: {session_id}")
        try:
            unlock_payload = {
                "command": "UNLOCK",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            payload_str = json.dumps(unlock_payload)
            # Keep this log
            logger.debug(
                f"Publishing unlock payload: {payload_str} to topic {TOPIC_UNLOCK_COMMAND}")
            result, mid = self.client.publish(
                TOPIC_UNLOCK_COMMAND, payload=payload_str, qos=1)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(
                    f"Published UNLOCK command for session/event: {session_id} (MID: {mid})")
            else:
                logger.error(
                    f"Failed to publish UNLOCK command (Result: {result}) for session/event: {session_id}")
        except Exception as e:
            logger.error(
                f"Error publishing unlock command: {e}", exc_info=True)

    # Restore original _send_and_log_notification structure (keeping added logs)
    def _send_and_log_notification(self, notification: Notification):
        """Helper method to send notification and log to history."""
        logger.debug(
            # Keep this log
            f"Entering _send_and_log_notification for event type: {notification.event_type.value}")
        sent = self.notification_service.send_notification(notification)
        # Keep this log
        logger.debug(
            f"Result of notification_service.send_notification: {sent}")
        if sent:
            notification.status = "Sent"
        else:
            notification.status = "Send_Failed"
        # Keep this log
        logger.debug(f"Set notification status to: {notification.status}")

        # --- Serialize the notification data just before saving ---
        # Use model_dump(mode='json') which handles nested UUIDs etc.
        try:
            notification_data_dict = notification.model_dump(mode='json')
            logger.debug(
                "Successfully dumped notification model to JSON-compatible dict.")
            # Keep this log
            logger.debug(
                f"Calling db_service.save_notification_to_history with status: {notification.status}")
            # Pass the dictionary instead of the object
            self.db_service.save_notification_to_history(
                notification_data_dict)
        except Exception as dump_or_save_err:
            logger.error(
                f"Error dumping notification or saving to history: {dump_or_save_err}", exc_info=True)
            # Avoid trying to save again if dumping failed, but maybe log a basic error record?
            # Or potentially try saving with minimal data if appropriate.

        # Keep this log
        logger.debug(
            f"Exiting _send_and_log_notification for event type: {notification.event_type.value}")
