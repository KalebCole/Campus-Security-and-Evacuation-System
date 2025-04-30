import paho.mqtt.client as mqtt  # Correct import
import json
import logging  # Correct import
import base64
import ssl  # Add ssl import for TLS
from datetime import datetime, timedelta
import time  # Added for reconnection delays
from threading import Timer  # Added for reconnection timer
from typing import Dict, Any, Optional, List, Union, Tuple
import uuid
import socket
import random
import string
import sqlalchemy.exc  # Add import for SQLAlchemy exceptions
import threading
import os
from flask import url_for  # <-- ADDED IMPORT

# Use relative imports
from ..core.config import Config
from .database import DatabaseService
from .face_recognition_client import FaceRecognitionClient, FaceRecognitionClientError
from ..models.session import Session as SessionModel
from ..models.notification import Notification, NotificationType, SeverityLevel
from .notification_service import NotificationService
from .storage_service import upload_image_to_supabase

# Setup logging
logger = logging.getLogger(__name__)  # Initialize logger correctly


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

        # Reset emergency state on initialization
        self.app.emergency_active = False
        logger.info(
            "Emergency state reset to False during MQTT service initialization")

        self.broker_address = Config.MQTT_BROKER_ADDRESS
        self.broker_port = Config.MQTT_BROKER_PORT

        # Reconnection state tracking
        self.reconnect_attempts = 0
        # Maximum delay between reconnection attempts (seconds)
        self.reconnect_max_delay = 60
        # Initial delay between reconnection attempts (seconds)
        self.reconnect_base_delay = 1
        # Maximum number of reconnection attempts (0 = unlimited)
        self.reconnect_max_attempts = 20
        self.reconnect_timer = None  # Timer object for reconnection

        # Track sessions currently being processed to prevent concurrency issues
        self._processing_session_ids = set()
        self._session_lock = threading.Lock()  # Added lock for session processing

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

        # --- Configure TLS ---
        logger.info(f"Configuring TLS with CA cert: certs/emqxsl-ca.crt")
        try:
            self.client.tls_set(
                ca_certs="/app/certs/emqxsl-ca.crt",
                cert_reqs=ssl.CERT_REQUIRED,
                # tls_version=ssl.PROTOCOL_TLSv1_2 # Optional: Specify TLS version if needed
            )
            logger.info("TLS successfully configured for MQTT client.")
        except FileNotFoundError:
            logger.error(
                "MQTT CA certificate file not found at certs/emqxsl-ca.crt. TLS not enabled.")
        except ssl.SSLError as e:
            logger.error(f"SSL error configuring TLS: {e}. TLS not enabled.")
        except Exception as e:
            logger.error(
                f"Unexpected error configuring TLS: {e}. TLS not enabled.")

        # --- Set Username/Password (if provided in config) ---
        if Config.MQTT_USERNAME and Config.MQTT_PASSWORD:
            logger.info(f"Setting MQTT username: {Config.MQTT_USERNAME}")
            self.client.username_pw_set(
                Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
        elif Config.MQTT_USERNAME:
            logger.warning(
                "MQTT_USERNAME is set but MQTT_PASSWORD is not. Authentication might fail.")
        else:
            logger.info(
                "MQTT username/password not set in config, attempting anonymous connection.")
        # --- End Username/Password ---

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

            # Run diagnostics before the initial connection attempt
            self._log_connection_diagnostics()

            self.client.connect(self.broker_address, self.broker_port, 60)
            self.client.loop_start()
            logger.info("MQTT client loop started.")
        except Exception as e:
            logger.error(
                f"Failed to connect to MQTT broker: {e}", exc_info=True)
            # If initial connection fails, start reconnection process
            self._schedule_reconnect()

    def disconnect(self):
        """Disconnect from the MQTT broker gracefully."""
        logger.info("Disconnecting from MQTT broker...")
        # Cancel any pending reconnect timers
        if self.reconnect_timer:
            self.reconnect_timer.cancel()
            self.reconnect_timer = None
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker.")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when the client connects to the MQTT broker."""
        if rc == 0:
            logger.info(
                f"Successfully connected to MQTT broker (Return Code: {rc})")
            # Reset reconnection state on successful connection
            self.reconnect_attempts = 0

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
            # On connection failure, start reconnection process (even when called within reconnect)
            self._schedule_reconnect()

    def _on_disconnect(self, client, userdata, rc):
        """Callback when the client disconnects from the MQTT broker."""
        logger.warning(f"Disconnected from MQTT broker with result code: {rc}")
        # Only implement reconnection logic for unexpected disconnects (rc != 0)
        if rc != 0:
            logger.error(
                "Unexpected MQTT disconnection. Attempting to reconnect...")
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt with exponential backoff."""
        # Cancel any existing reconnection timer
        if self.reconnect_timer:
            self.reconnect_timer.cancel()

        # Check if we've exceeded maximum attempts (if configured)
        if self.reconnect_max_attempts > 0 and self.reconnect_attempts >= self.reconnect_max_attempts:
            logger.error(
                f"Maximum reconnection attempts ({self.reconnect_max_attempts}) reached. Giving up.")
            return

        # Calculate delay with exponential backoff
        delay = min(self.reconnect_base_delay *
                    (2 ** self.reconnect_attempts), self.reconnect_max_delay)

        # Add some jitter to avoid reconnection storms (±20%)
        jitter = random.uniform(0.8, 1.2)
        delay = delay * jitter

        self.reconnect_attempts += 1
        logger.info(
            f"Scheduling reconnection attempt {self.reconnect_attempts} in {delay:.2f} seconds")

        # Schedule reconnection
        self.reconnect_timer = Timer(delay, self._reconnect)
        # Ensure timer thread doesn't block app shutdown
        self.reconnect_timer.daemon = True
        self.reconnect_timer.start()

    def _reconnect(self):
        """Attempt to reconnect to the MQTT broker."""
        logger.info(
            f"Attempting to reconnect to MQTT broker (attempt {self.reconnect_attempts})...")

        # Add diagnostic logging
        self._log_connection_diagnostics()

        try:
            # Stop the loop if it's still running
            self.client.loop_stop()
            # Attempt to reconnect
            self.client.reconnect()
            # Restart the loop
            self.client.loop_start()
            logger.info(
                f"Reconnection attempt {self.reconnect_attempts} successful")
        except Exception as e:
            logger.error(
                f"Reconnection attempt {self.reconnect_attempts} failed: {e}", exc_info=True)
            # Schedule next reconnection attempt
            self._schedule_reconnect()

    def _log_connection_diagnostics(self):
        """Log diagnostic information about the MQTT connection."""
        try:
            import os
            import socket

            # Log broker details
            logger.info(f"MQTT Broker Address: {self.broker_address}")
            logger.info(f"MQTT Broker Port: {self.broker_port}")

            # Check if certificate file exists
            cert_path = "/app/certs/emqxsl-ca.crt"
            if os.path.exists(cert_path):
                cert_size = os.path.getsize(cert_path)
                logger.info(
                    f"Certificate file exists at {cert_path} (size: {cert_size} bytes)")
            else:
                logger.error(f"Certificate file NOT found at {cert_path}")

            # List contents of certs directory
            certs_dir = "/app/certs"
            if os.path.exists(certs_dir):
                files = os.listdir(certs_dir)
                logger.info(f"Contents of {certs_dir}: {files}")
            else:
                logger.error(f"Certs directory NOT found at {certs_dir}")

            # Try to resolve broker hostname
            try:
                ip_address = socket.gethostbyname(self.broker_address)
                logger.info(
                    f"Resolved broker address {self.broker_address} to IP: {ip_address}")
            except socket.gaierror:
                logger.error(
                    f"Could not resolve broker address: {self.broker_address}")

            # Try a basic socket connection to test network reachability
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex((self.broker_address, self.broker_port))
                if result == 0:
                    logger.info(
                        f"Socket connection test to {self.broker_address}:{self.broker_port} successful")
                else:
                    logger.error(
                        f"Socket connection test to {self.broker_address}:{self.broker_port} failed with error code {result}")
                s.close()
            except Exception as e:
                logger.error(f"Socket connection test failed: {e}")

        except Exception as diag_err:
            logger.error(
                f"Error during connection diagnostics: {diag_err}", exc_info=True)

    def _on_message(self, client, userdata, msg):
        """
        Callback when a message is received from the MQTT broker.
        Robustly handles BOMs, skips non-JSON or retained payloads,
        and routes valid JSON to the appropriate handler.
        """
        raw = msg.payload
        topic = msg.topic

        # 0) Drop any retained messages (e.g. old binary blobs)
        if msg.retain:
            logger.debug(f"Ignoring retained message on topic '{topic}'")
            return

        # 1) Strip BOMs and decode
        if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            # UTF-16LE or UTF-16BE BOM
            try:
                text = raw.decode('utf-16')
            except UnicodeDecodeError:
                logger.warning(
                    f"Unable to decode UTF-16 payload on '{topic}', skipping")
                return
        else:
            # Remove UTF-8 BOM if present
            raw_no_bom = raw.lstrip(b'\xef\xbb\xbf')
            try:
                text = raw_no_bom.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(
                    f"Unable to decode UTF-8 payload on '{topic}', skipping")
                return

        # 2) Quick sanity check: must start with a JSON object
        text = text.lstrip()
        if not text.startswith('{'):
            logger.warning(f"Dropping non-JSON payload on '{topic}'")
            return

        logger.info(f"Received message on topic '{topic}'")
        logger.debug(f"Decoded payload (first 200 chars): {text[:200]}")

        # 3) Parse JSON
        try:
            payload_dict = json.loads(text)
            logger.debug("JSON decoded successfully.")
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode JSON on '{topic}': {e}", exc_info=True)
            return

        # 4) Route based on topic
        if topic == TOPIC_SESSION_DATA:
            logger.debug("Routing to _handle_session_message...")
            self._handle_session_message(payload_dict)
        elif topic == TOPIC_EMERGENCY:
            logger.debug("Routing to _handle_emergency_message...")
            self._handle_emergency_message(payload_dict)
        else:
            logger.warning(f"Received message on unhandled topic: '{topic}'")

    def _handle_session_message(self, payload: Dict[str, Any]):
        """Process messages received on the session data topic."""
        # print the topic
        logger.info(f"Received session message on topic: {TOPIC_SESSION_DATA}")
        logger.info("Handling session message...")
        # Keep this log

        # --- ADDED: Lock and Check for Concurrent Processing ---
        session_id = payload.get('session_id')
        if not session_id:
            logger.error(
                "Session message received without session_id. Cannot process.")
            return

        # Acquire lock before checking/modifying the set
        with self._session_lock:
            if session_id in self._processing_session_ids:
                logger.warning(
                    f"Session {session_id} is already being processed. Skipping duplicate message.")
                return  # Return while still holding lock to prevent the finally block from removing prematurely
            # If not already processing, add it to the set
            self._processing_session_ids.add(session_id)
        # Lock is released here
        # -------------------------------------------------------

        # Initialize variables within the main try block
        # (Moved these down to be after the concurrency check)
        new_embedding: Optional[List[float]] = None
        employee_record = None
        verification_result: Optional[Dict[str, Any]] = None
        access_granted: bool = False
        verification_method: str = "NONE"
        confidence: Optional[float] = None
        image_bytes: Optional[bytes] = None
        employee_id_for_log: Optional[uuid.UUID] = None
        notification_to_send: Optional[Notification] = None
        storage_url: Optional[str] = None
        session_data: Optional[SessionModel] = None

        try:
            # 1. Validate payload (moved inside main try)
            try:
                logger.debug("Attempting Pydantic validation...")
                session_data = SessionModel(**payload)
                logger.info(
                    f"Validated session data for session_id: {session_id}")
            except Exception as e:
                logger.error(
                    # Don't need full traceback for validation
                    f"Invalid session payload received for {session_id}: {e}", exc_info=False)
                logger.debug(f"Invalid payload details: {payload}")
                # Don't create notification here, let finally handle cleanup
                return  # Exit if validation fails

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

                    # CHANGE 1: Wrap the Supabase upload call with app context
                    with self.app.app_context():
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
                    # if session_data.face_detected:
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
                    # else:
                        # If face_detected is false, skip embedding call
                        # logger.info(
                        #     f"face_detected is False. Skipping face embedding generation for session {session_data.session_id}.")
                        # new_embedding = None  # Ensure embedding is None

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
                    # *** ADDED: Log embedding values before comparison ***
                    logger.debug(
                        f"  New Embedding (first 10): {str(new_embedding[:10])}...")
                    # Ensure employee_record.face_embedding is treated as a list for slicing
                    # REMOVED: db_embedding_list = list(employee_record.face_embedding)
                    # Log the raw embedding type and its first elements converted to list for display
                    db_embedding_raw = employee_record.face_embedding
                    # Explicitly convert each numpy float to standard Python float for logging
                    db_embedding_log_repr = [float(
                        x) for x in db_embedding_raw[:10]] if db_embedding_raw is not None else None
                    logger.debug(
                        f"  DB Embedding (first 10):  {str(db_embedding_log_repr)}... (Type: {type(db_embedding_raw)})")
                    # ***************************************************

                    # NOTE: This now calls the *local* verify_embeddings in the client,
                    # which calculates cosine similarity based on the configured threshold.
                    # Pass the raw embedding object retrieved from the database
                    verification_result = self.face_client.verify_embeddings(
                        new_embedding, db_embedding_raw)  # Use db_embedding_raw

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
                    distance_threshold = 1 - Config.FACE_VERIFICATION_THRESHOLD
                    # Keep this log
                    logger.debug(
                        f"Calling db_service.find_similar_embeddings for session {session_data.session_id}")
                    # --- ADD THIS LINE ---
                    logger.debug(
                        f"  Using new_embedding (first 10 + length): {str(new_embedding[:10])}... (Length: {len(new_embedding) if new_embedding else 'None'})")
                    # ---------------------
                    potential_matches_raw = self.db_service.find_similar_embeddings(
                        new_embedding, threshold=1, limit=3)
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
                # Keep internal logic context, but log a more specific method string
                verification_method = "NO_FACE_OR_RFID"  # Changed from "INCOMPLETE_DATA"
                access_granted = False
                # Keep this log
                logger.warning(
                    f"Entering INCOMPLETE_DATA branch (logging as NO_FACE_OR_RFID). Session: {session_data.session_id}")
                # Keep this log
                logger.debug(
                    f"Insufficient data (no employee record and no new embedding) for verification. Session: {session_data.session_id}. Access denied.")
                if notification_to_send is None:
                    # Keep this log
                    logger.debug(
                        "Creating notification for incomplete data (NO_FACE_OR_RFID) as no prior notification was set.")
                    notification_to_send = Notification(
                        event_type=NotificationType.SYSTEM_ERROR,  # Or maybe a more specific type?
                        severity=SeverityLevel.WARNING,
                        session_id=session_data.session_id,
                        message="No face detected or RFID tag presented for verification."
                    )
                else:
                    # Keep this log
                    logger.debug(
                        "Skipping notification for incomplete data as a prior notification was already set.")

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
            logger.debug("Entering access logging logic.")
            access_log_record = self.db_service.log_access_attempt(
                session_id=session_data.session_id,
                verification_method=verification_method,
                access_granted=access_granted,
                employee_id=employee_id_for_log,
                verification_confidence=confidence
                # review_status is handled internally by log_access_attempt
            )
            if access_log_record:
                logger.debug("Access attempt logged successfully.")
            else:
                # Log error but don't necessarily stop processing
                logger.error(
                    f"Failed to log access attempt for session {session_data.session_id} (db_service returned None).")
                # Consider creating a SYSTEM_ERROR notification here?
                # notification_to_send = ...

            # 7. Publish Unlock Command (if access granted)
            logger.debug(
                f"Checking if access_granted is True to publish unlock. access_granted={access_granted}")
            if access_granted:
                self._publish_unlock(session_data.session_id)

            # --- 8. Create Notification (Moved creation here) ---
            logger.debug("Entering notification creation logic.")
            # Construct notification based on the final outcome
            # Default values
            notif_type = NotificationType.DEFAULT
            notif_severity = SeverityLevel.INFO
            notif_message = "Access event processed."
            notif_image_url = None  # Use storage_url if needed
            notif_additional_data = {}

            # Customize based on verification method and outcome
            employee_name = employee_record.name if employee_record else None

            # Add common data
            if employee_name:
                notif_additional_data['employee_name'] = employee_name
            if confidence is not None:
                notif_additional_data['confidence'] = confidence

            # --- Generate Review URL within App Context ---
            review_url = None
            # Check if review might be needed or beneficial
            if verification_method in ['FACE_ONLY_PENDING_REVIEW', 'RFID_ONLY_PENDING_REVIEW', 'FACE_VERIFICATION_FAILED'] or not access_granted:
                try:
                    with self.app.app_context():  # Ensure we have app context
                        review_url = url_for('admin_bp.get_review_details',
                                             session_id=session_data.session_id,
                                             _external=True)
                        # Add to additional data
                        notif_additional_data['review_url'] = review_url
                        logger.debug(f"Generated review URL: {review_url}")
                except Exception as url_err:
                    logger.error(
                        f"Failed to generate review URL for session {session_data.session_id}: {url_err}", exc_info=True)
            # -------------------------------------------- >

            if verification_method == "RFID+FACE":
                if access_granted:
                    notif_type = NotificationType.ACCESS_GRANTED
                    notif_severity = SeverityLevel.INFO
                    notif_message = f"Access granted to {employee_name or 'employee'} via RFID+Face."
                    # notif_additional_data['confidence'] = confidence
                else:
                    # This case shouldn't happen with current logic (failed verification goes to FACE_VERIFICATION_FAILED)
                    # But handle defensively
                    notif_type = NotificationType.FACE_NOT_RECOGNIZED  # Or a specific failure type
                    notif_severity = SeverityLevel.WARNING
                    notif_message = f"RFID+Face access denied for {employee_name or 'employee'}. Confidence: {confidence:.4f}"
                    notif_image_url = storage_url

            elif verification_method == "FACE_ONLY_PENDING_REVIEW":
                notif_type = NotificationType.MANUAL_REVIEW_REQUIRED
                notif_severity = SeverityLevel.WARNING
                notif_message = f"Face detected without RFID. Manual review needed."
                notif_image_url = storage_url
                # Add potential matches if needed for notification
                # potential_matches = self.db_service.find_similar_embeddings(new_embedding)
                # notif_additional_data['potential_matches'] = [...] # Serialize matches

            elif verification_method == "RFID_ONLY_PENDING_REVIEW":
                notif_type = NotificationType.MANUAL_REVIEW_REQUIRED
                notif_severity = SeverityLevel.WARNING
                notif_message = f"RFID tag '{rfid_tag}' ({employee_name or 'Unknown'}) detected without face. Manual review needed."
                notif_image_url = storage_url

            elif verification_method == "FACE_VERIFICATION_FAILED":
                notif_type = NotificationType.MANUAL_REVIEW_REQUIRED  # Still needs review
                notif_severity = SeverityLevel.WARNING
                notif_message = f"Face verification failed for {employee_name or 'employee'} (RFID: {rfid_tag}). Confidence: {confidence:.4f}. Manual review needed."
                notif_image_url = storage_url

            elif verification_method == "UNKNOWN_RFID":
                notif_type = NotificationType.RFID_NOT_FOUND
                notif_severity = SeverityLevel.WARNING
                notif_message = f"Unknown RFID tag '{rfid_tag}' presented."
                notif_image_url = storage_url  # Include image if available

            elif verification_method == "NO_FACE_EMBEDDING":
                notif_type = NotificationType.FACE_NOT_RECOGNIZED  # Or a setup warning?
                notif_severity = SeverityLevel.WARNING
                notif_message = f"Access attempt by {employee_name or 'employee'} (RFID: {rfid_tag}) failed: No reference face embedding stored."
                # notif_image_url = storage_url # Probably not needed

            # --- Final Notification Object Creation ---
            if notif_type != NotificationType.DEFAULT:
                notification_to_send = Notification(
                    event_type=notif_type,
                    severity=notif_severity,
                    timestamp=datetime.utcnow().isoformat(),
                    session_id=session_data.session_id,
                    user_id=str(
                        employee_id_for_log) if employee_id_for_log else None,
                    message=notif_message,
                    image_url=notif_image_url,
                    additional_data=notif_additional_data
                    # Status is set later in _send_and_log_notification
                )
                logger.info(
                    f"Notification created: Type={notif_type.name}, Severity={notif_severity.name}")
            else:
                logger.debug(
                    "No specific notification condition met for this session outcome.")

        except sqlalchemy.exc.SQLAlchemyError as db_err:
            logger.error(
                f"Database error during session {session_id} processing: {db_err}", exc_info=True)

        finally:
            # --- ADDED: Remove session ID from processing set ---
            if session_id in self._processing_session_ids:
                with self._session_lock:
                    self._processing_session_ids.remove(session_id)
                    logger.debug(
                        f"Removed session {session_id} from processing set.")
            # ---------------------------------------------------

            # --- Notification Sending Logic (Moved to finally block) ---
            logger.debug("Entering notification sending logic.")
            if notification_to_send:
                logger.info(
                    f"Notification created: Type={notification_to_send.event_type.name}, Severity={notification_to_send.severity.name}")
                # Log details before sending for debugging
                logger.debug(
                    f"Notification details before sending: {notification_to_send.model_dump()}")
                try:
                    # Use existing session_id variable
                    self._send_and_log_notification(notification_to_send)
                except Exception as notify_err:
                    logger.error(
                        f"Error sending/logging notification for session {session_id}: {notify_err}", exc_info=True)
            else:
                logger.debug("No notification generated for this session.")
            # --- End Notification Sending ---

    def _handle_emergency_message(self, payload: Dict[str, Any]):
        """Process messages received on the emergency topic."""
        logger.info(f"Received session message on topic: {TOPIC_SESSION_DATA}")
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
        # Schedule automatic reset after 15 seconds
        reset_timer = threading.Timer(15.0, self._reset_emergency_state)
        reset_timer.daemon = True  # Daemon thread won't prevent app shutdown
        reset_timer.start()
        logger.info(
            "Scheduled automatic reset of emergency state after 15 seconds")
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
        # self._publish_unlock(session_id="EMERGENCY")

    def _reset_emergency_state(self):
        """Reset the emergency state to False after timeout."""
        logger.warning(
            "Automatically resetting emergency state to inactive after timeout")
        self.app.emergency_active = False

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
