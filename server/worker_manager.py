import threading
import time
import logging
from app_config import Config
from notification_service import NotificationType
from datetime import datetime
import numpy as np
from model.model_integration import cosineDistance

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages background worker thread for session management and verification"""

    def __init__(self, session_manager, notification_service, timeout=Config.SESSION_TIMEOUT):
        self.session_manager = session_manager
        self.notification_service = notification_service
        self.timeout = timeout

        # Single worker thread
        self.worker_thread = None
        self.is_running = False
        self.system_active = False

    def start_worker(self, interval=2):
        """Start the worker thread that handles both verification and cleanup"""
        # Set flags
        self.is_running = True
        self.system_active = True

        # Define the worker function
        def worker_function():
            logger.info("[Worker] Worker thread started")

            while self.is_running:
                try:
                    if self.system_active:
                        # Process complete sessions
                        self._process_complete_sessions()

                        # Clean expired sessions
                        self._clean_stale_sessions()

                    # Sleep between checks
                    time.sleep(interval)

                except Exception as e:
                    logger.error(f"[Worker] Error in worker thread: {str(e)}")

        # Create and start the thread if not already running
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(
                target=worker_function,
                daemon=True
            )
            self.worker_thread.start()
            logger.info(
                f"[Worker] Worker thread started with interval {interval}s")

        return self.worker_thread

    def stop_worker(self):
        """Stop the worker thread"""
        self.system_active = False
        logger.info("[Worker] Worker thread paused (system inactive)")
        return True

    def terminate_worker(self):
        """Completely terminate the worker thread"""
        self.is_running = False

        # Wait for the thread to finish if it exists
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)

        # Reset the thread
        self.worker_thread = None
        logger.info("[Worker] Worker thread terminated")

    def _clean_stale_sessions(self):
        """Clean up sessions that have exceeded the timeout period"""
        try:
            cleaned = self.session_manager.clean_expired_sessions()
            if cleaned > 0:
                logger.info(
                    f"[Session Cleanup] Cleaned {cleaned} stale sessions")
        except Exception as e:
            logger.error(
                f"[Session Cleanup] Error cleaning stale sessions: {str(e)}")

    def _process_complete_sessions(self):
        """Find and process sessions with both RFID and image data"""
        sessions = self.session_manager.get_all_sessions()

        for session_id, session in sessions.items():
            try:
                # Check if this session has both pieces of data needed
                # FIX: Check for existence of attributes properly
                has_rfid = hasattr(
                    session, 'rfid_tag') and session.rfid_tag is not None
                has_image = hasattr(
                    session, 'image_data') and session.image_data is not None

                if has_rfid and has_image:
                    logger.info(
                        "[Verification] Processing complete session %s", session_id)

                    # Perform verification directly
                    result = self._perform_verification(session)

                    # Log the result
                    logger.info(
                        "[Verification] Result for %s: %s", session_id, result['status'])

                    # Remove the session after processing
                    self.session_manager.remove_session(session_id)
            except (KeyError, ValueError, AttributeError, TypeError) as e:
                logger.error(
                    "[Verification] Error processing session %s: %s", session_id, str(e))

    # TODO: Remove this method from the final version and abstract it into a separate utility
    # This method should be replaced with a call to a separate verification service
    def _perform_verification(self, session):
        """Verify user identity using RFID and facial data"""
        try:
            # Get user data and embeddings
            user_data = session.user_data
            if user_data is None:
                logger.error(
                    f"[Verification] No user data found for session {session.session_id}")
                return {"status": "error", "message": "No user data found"}

            user_embedding = user_data.get("facial_embedding")

            # if embedding is None or if it's a numpy array with no elements
            if user_embedding is None or (isinstance(user_embedding, np.ndarray) and user_embedding.size == 0):
                logger.error(
                    f"[Verification] No facial embedding found for user {user_data.get('name', 'unknown')}")
                return {"status": "error", "message": "No facial embedding found for user"}

            session_embedding = session.embedding
            if session_embedding is None or (isinstance(session_embedding, np.ndarray) and session_embedding.size == 0):
                logger.error(f"[Verification] No session embedding available")
                return {"status": "error", "message": "No session embedding available"}

            # Calculate similarity
            # debug log to make sure we get here
            logger.info(
                f"[Verification] Calculating similarity for {user_data['name']} and session {session.session_id}")
            # Calculate similarity using the imported function
            #
            similarity = cosineDistance(session_embedding, user_embedding)

            logger.info(f"Similarity: {similarity}")

            if isinstance(similarity, (np.ndarray, np.generic)):
                similarity = float(similarity)

            # Make verification decision
            SIMILARITY_THRESHOLD = Config.SIMILARITY_THRESHOLD

            # print the similarity type and value to make sure its a float
            print(f"Similarity type: {type(similarity)}")
            print(f"Similarity value: {similarity}")

            print("before verification_successful")
            verification_successful = similarity >= SIMILARITY_THRESHOLD
            print("after verification_successful")
            timestamp = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            # Send appropriate notification and return result
            if verification_successful:
                self.notification_service.send(NotificationType.ACCESS_GRANTED, {
                    "name": user_data['name'],
                    "rfid_tag": session.rfid_tag,
                    "timestamp": timestamp,
                    "similarity": similarity,
                    # Add the role from user data
                    "role": user_data.get('role', 'Unknown')
                })

                return {
                    "status": "success",
                    "message": f"Access granted for {user_data['name']}",
                    "similarity": float(similarity)
                }
            else:
                self.notification_service.send(NotificationType.FACE_NOT_RECOGNIZED, {
                    "name": user_data['name'],
                    "rfid_tag": session.rfid_tag,
                    "timestamp": timestamp,
                    "similarity": similarity
                })

                return {
                    "status": "failure",
                    "message": "Face verification failed",
                    "similarity": float(similarity)
                }

        except Exception as e:
            logger.error(f"[Verification] Error during verification: {str(e)}")
            return {"status": "error", "message": str(e)}
