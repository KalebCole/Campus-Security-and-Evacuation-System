"""Routes for handling verification operations (RFID, image processing, sessions)."""
import logging
import numpy as np
import threading
import time
import cv2
from datetime import datetime
from flask import request, jsonify

from . import routes_bp
from app_config import Config
from model.model_integration import generate_embedding
from data.session import SessionType
from session_manager import SessionManager
from notifications.notification_service import NotificationService, NotificationType
from worker_manager import WorkerManager
from supabase_client import supabase

# Configure logging
logger = logging.getLogger(__name__)

# Shared resources (these will be initialized in routes/__init__.py in the future)
notif_service = NotificationService()
session_manager = SessionManager()
worker_manager = WorkerManager(session_manager, notif_service)

# Thread lock for thread-safe session access
session_lock = threading.Lock()

# Session timeout in seconds
SESSION_TIMEOUT = 15

# Mocked user data for testing
mock_db = [
    {"id": 1, "name": "Bob", "role": "Supervisor", "rfid_tag": "123456",
        "facial_embedding": [0.1] * 128, "image_url": "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"},
    {"id": 2, "name": "Rob", "rfid_tag": "654321",
        "facial_embedding": [0.2] * 128, "role": "Software Engineer", "image_url": "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"},
    {"id": 3, "name": "Charlie", "rfid_tag": "789012",
        "facial_embedding": [0.3] * 128, "role": "Hardware Engineer",  "image_url": "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"}
]

# TODO: abstract this to a config file
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def query_user_by_rfid(rfid_tag, mock=False):
    """Query user by RFID tag from either mock database or actual database."""
    logger.info(
        f"[DB Query] Starting RFID query operation - RFID: {rfid_tag}, Mock Mode: {mock}")
    start_time = time.time()

    if mock:
        print(f"[Mock DB] Searching for RFID {rfid_tag}")
        for user in mock_db:
            if user["rfid_tag"] == rfid_tag:
                print(
                    f"[Mock DB] Found user for RFID {rfid_tag}: {user['name']}")
                return user
        print(f"[Mock DB] No user found for RFID {rfid_tag}")
        return None
    else:
        print(f"[Real DB] Querying database for RFID {rfid_tag}")
        try:
            response = supabase.table('users').select(
                '*').eq('rfid_tag', rfid_tag).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"[Real DB] Error querying database: {e}")
        return None


def query_all_users(mock=False):
    """
    Query all users from either mock database or actual database.
    """
    if mock:
        print("[Mock DB] Returning all users")
        return mock_db
    else:
        print("[Real DB] Querying all users from database")
        try:
            response = supabase.table('users').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"[Real DB] Error querying database: {e}")
        return []


def calculate_similarity(embedding1, embedding2):
    """Calculate similarity between two facial embeddings."""
    if len(embedding1) != 128 or len(embedding2) != 128:
        raise ValueError(
            f"Embeddings must be 128-dimensional. Got {len(embedding1)} and {len(embedding2)}")
    embedding1 = np.array(embedding1, dtype=np.float32)
    embedding2 = np.array(embedding2, dtype=np.float32)
    embedding1 /= np.linalg.norm(embedding1)
    embedding2 /= np.linalg.norm(embedding2)
    return np.dot(embedding1, embedding2)


def verify_user(rfid_tag=None, image_data=None, embedding=None, session_id=None):
    """Unified verification logic that handles all verification scenarios."""
    try:
        # Get or create session
        session = session_manager.get_session(session_id)
        if not session:
            # Create a new session if session_id not provided
            if rfid_tag:
                session = session_manager.create_session(
                    SessionType.RFID_RECEIVED)
            elif image_data is not None:
                session = session_manager.create_session(
                    SessionType.IMAGE_RECEIVED)
            else:
                return {"status": "error", "message": "No identification provided"}, 400
            session_id = session.session_id

        # Handle RFID input
        if rfid_tag:
            # Store RFID in session
            session_manager.update_session(
                session_id,
                rfid_tag=rfid_tag,
                session_type=SessionType.RFID_RECEIVED if not session.image_data else SessionType.VERIFICATION_COMPLETE
            )

            # Query and store user data if RFID provided
            if not hasattr(session, 'user_data') or not session.user_data:
                user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
                if not user:
                    # Send notification for RFID not found
                    notif_service.send(NotificationType.RFID_NOT_FOUND, {
                        "rfid_tag": rfid_tag,
                        "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
                    })
                    return {
                        "status": "failure",
                        "message": "No user found for provided RFID",
                        "session_id": session_id
                    }, 404

                # Store user data
                session_manager.update_session(session_id, user_data=user)

                # Send notification for RFID recognized
                notif_service.send(NotificationType.RFID_RECOGNIZED, {
                    "name": user['name'],
                    "rfid_tag": rfid_tag,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
                })

        # Handle image data input
        if image_data is not None:
            # Generate and store embedding
            if not embedding:
                embedding = generate_embedding(image_data)

            session_manager.update_session(
                session_id,
                image_data=image_data,
                embedding=embedding,
                session_type=SessionType.IMAGE_RECEIVED if not session.rfid_tag else session.session_type
            )

        # Determine request type and queue for verification
        if session.rfid_tag is not None and session.image_data is not None:
            # Verification worker will process this session
            logger.info(
                f"[Logic] Session {session_id} has both RFID and image, ready for verification")
            return {
                "status": "processing",
                "message": "RFID and image received, processing verification",
                "session_id": session_id
            }, 202

        elif session.rfid_tag:
            # RFID only - waiting for image
            return {
                "status": "pending_verification",
                "message": f"Suspected user: {session.user_data['name']}. Awaiting facial verification.",
                "session_id": session.session_id
            }, 202

        elif session.image_data:
            # Image only - waiting for RFID
            return {
                "status": "pending_verification",
                "message": "Image processed, awaiting RFID",
                "session_id": session.session_id
            }, 202

        else:
            return {
                "status": "error",
                "message": "No RFID or image provided",
                "session_id": session.session_id
            }, 400

    except Exception as e:
        logger.error(f"[Logic] Error in verify_user: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


@routes_bp.route('/rfid', methods=['POST'])
def handle_rfid():
    """
    Handle RFID tag input from the RFID client (Arduino).
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract RFID tag from the request
        rfid_tag = data.get('rfid_tag')
        if not rfid_tag:
            return jsonify({"error": "No RFID tag provided"}), 400

        # Check if a session ID was provided
        session_id = data.get('session_id')

        # Process the RFID tag
        result, status_code = verify_user(
            rfid_tag=rfid_tag, session_id=session_id)
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"[API] Error processing RFID request: {str(e)}")
        return jsonify({"error": str(e)}), 500


@routes_bp.route('/image', methods=['POST'])
def handle_image():
    """
    Handle image input from the ESP32 camera client.
    """
    try:
        # Extract image data from request
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            # Read the image
            image_data = cv2.imdecode(
                np.frombuffer(file.read(), np.uint8),
                cv2.IMREAD_COLOR
            )

            # Check if a session ID was provided
            session_id = request.form.get('session_id')

            # Process the image
            result, status_code = verify_user(
                image_data=image_data, session_id=session_id)
            return jsonify(result), status_code
        else:
            return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        logger.error(f"[API] Error processing image request: {str(e)}")
        return jsonify({"error": str(e)}), 500


@routes_bp.route('/session', methods=['GET'])
def get_session():
    """
    Get or create a session ID for the client.
    """
    # Check if system is active before creating a session
    from .system_routes import system_state

    if not system_state.get("active", False):
        return jsonify({
            "error": "System not activated",
            "message": "Please activate the system first"
        }), 400

    # Create a new session
    session = session_manager.create_session(SessionType.RFID_RECEIVED)

    return jsonify({
        "success": True,
        "session_id": session.session_id,
        "expires_in": SESSION_TIMEOUT
    }), 200


@routes_bp.route('/status/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """
    Get the status of a verification session.
    """
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({
            "error": "Session not found",
            "message": f"No session found with ID {session_id}"
        }), 404

    # Return appropriate status based on session state
    if session.verification_result:
        return jsonify({
            "status": "completed",
            "result": session.verification_result
        }), 200
    elif session.rfid_tag and session.image_data:
        return jsonify({
            "status": "processing",
            "message": "Both RFID and image received, processing verification"
        }), 202
    elif session.rfid_tag:
        return jsonify({
            "status": "waiting_for_image",
            "message": "RFID received, waiting for image"
        }), 202
    elif session.image_data:
        return jsonify({
            "status": "waiting_for_rfid",
            "message": "Image received, waiting for RFID"
        }), 202
    else:
        return jsonify({
            "status": "new",
            "message": "Session created, waiting for inputs"
        }), 200
