from app_config import Config
import logging
import cv2
from flask import Blueprint, request, jsonify
from supabase_client import supabase
from notifications.notification_service import NotificationService, NotificationType
import numpy as np
import time
import threading
from datetime import datetime
# Add the model directory
from model.model_integration import generate_embedding
from data.session import SessionType
from session_manager import SessionManager
from worker_manager import WorkerManager


# =======================
# List of TODOs
# =======================
"""
# TODO: Figure out how to have the clients have the same session_id for the same session
    # Clients are the following: ESP32, Web App, Arduino R4 Uno for RFID

# TODO: Add the logic for the server to send the unlock signal to the Arduino R4 Uno

# TODO: What to do when face is not detected? should this trigger a new image to be taken before a timeout?
"""


# =======================
# Setup and Configuration
# =======================

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

routes_bp = Blueprint('routes', __name__)


# Initialize system state and session manager
system_state = {
    "active": False,
    "last_activity": None
}

notif_service = NotificationService()
session_manager = SessionManager()
worker_manager = WorkerManager(session_manager, notif_service)

# Thread lock for thread-safe session access
session_lock = threading.Lock()

# Timeout configuration
SESSION_TIMEOUT = 15
SYSTEM_TIMEOUT = 15  # system timeout in seconds

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

# TODO: abstract this to a utility file


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# =======================
# Database Operations
# =======================
# TODO: Move these functions to a separate file in the data layer


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

    :param mock: Boolean flag to indicate whether to use the mock database.
    :return: List of user objects.
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
# Calculate similarity between two embeddings


# TODO: move this function to model_operations.py
def calculate_similarity(embedding1, embedding2):
    if len(embedding1) != 128 or len(embedding2) != 128:
        raise ValueError(
            f"Embeddings must be 128-dimensional. Got {len(embedding1)} and {len(embedding2)}")
    embedding1 = np.array(embedding1, dtype=np.float32)
    embedding2 = np.array(embedding2, dtype=np.float32)
    embedding1 /= np.linalg.norm(embedding1)
    embedding2 /= np.linalg.norm(embedding2)
    return np.dot(embedding1, embedding2)

# =======================
# Logic to Handle the Inputs
# =======================


def verify_user(rfid_tag=None, image_data=None, embedding=None, session_id=None):
    """Unified verification logic that handles all verification scenarios

    Args:
        rfid_tag: Optional RFID tag
        image_data: Optional image data
        embedding: Optional pre-computed embedding
        session_id: Optional session ID

    Returns:
        tuple: (result_dict, status_code)
    """
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

        # we have a session already. we get rfid_tag from the client
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

        # we have a session already. we get image_data from the client
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
            return {"status": "error", "message": "Insufficient identification data"}, 400

    except Exception as e:
        logger.error(f"Error in verify_user: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500


# =======================
# Routes
# =======================

# route to test if we can access this blueprint

@routes_bp.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "success", "message": "API test is working!"}), 200


@routes_bp.route('/activate', methods=['GET'])
def activate_system():
    """Activate the system"""
    system_state["active"] = True
    system_state["last_activity"] = time.time()
    # start the worker to clean up stale sessions
    worker_manager.start_worker()

    logger.info(f"[System] System activated. State: {system_state}")
    return jsonify({"status": "success", "message": "System activated"}), 200


# Changed from /deactivate
@routes_bp.route('/deactivate', methods=['GET'])
def deactivate_system():
    """Deactivate the system"""
    system_state["active"] = False
    system_state["last_activity"] = None
    # stop the worker to clean up stale sessions
    worker_manager.stop_worker()
    logger.info(f"[System] System manually deactivated. State: {system_state}")
    logger.info(
        f"[System] Amount of sessions: {len(session_manager.get_all_sessions())}")
    return jsonify({"status": "success", "message": "System deactivated"}), 200


# Route to handle RFID data from the Mega
@routes_bp.route('/rfid', methods=['POST'])
def receive_rfid():
    """Handle RFID data from the Arduino Mega"""
    logger.info("[API] Received RFID request")

    if not system_state["active"]:
        logger.warning("[System] Received RFID while system inactive")
        return jsonify({
            "status": "error",
            "message": "System not activated"
        }), 400

    try:
        data = request.get_json()
        rfid_tag = data.get('rfid_tag')
        session_id = data.get('session_id')
        logger.info(f"[API] Processing RFID data: {rfid_tag}")

        # Use verify_user to handle all logic
        result, status_code = verify_user(
            rfid_tag=rfid_tag, session_id=session_id)
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"[API] Error processing RFID: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to process RFID: {str(e)}"
        }), 500


@routes_bp.route('/image', methods=['POST'])
def receive_image():
    """Handle image data from clients"""
    logger.info("[API] Received image upload request")

    if not system_state["active"]:
        logger.warning("[System] Received image while system inactive")
        return jsonify({
            "status": "error",
            "message": "System not activated"
        }), 400

    try:
        if 'imageFile' not in request.files:
            logger.warning("[API] No image file in request")
            return jsonify({"error": "No image file provided"}), 400

        image_file = request.files['imageFile']
        session_id = request.form.get('session_id')

        # Process image
        image_bytes = image_file.read()
        image = cv2.imdecode(np.frombuffer(
            image_bytes, np.uint8), cv2.IMREAD_COLOR)

        # Use verify_user to handle all logic
        result, status_code = verify_user(
            image_data=image, session_id=session_id)
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"[API] Error processing image: {str(e)}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500


@routes_bp.route('/session', methods=['GET'])
def get_session_id():
    '''
    Get a session id for the client to use for the session
    '''
    # check if system is active
    if not system_state["active"]:
        return jsonify({"status": "error", "message": "System not activated"}), 400

    # check if there is a session that already exists in the session manager dictionary
    session_id = session_manager.get_session_id()
    if session_id is not None:
        return jsonify({"status": "success", "session_id": session_id}), 200

    # create a unique session id and give it to the client
    session_id = session_manager.create_session_id()
    return jsonify({"status": "success", "session_id": session_id}), 200


@routes_bp.route('/status/<session_id>', methods=['GET'])
def check_verification_status(session_id):
    """Check the status of a verification request"""
    try:
        session = session_manager.get_session(session_id)

        if not session:
            return jsonify({
                "status": "error",
                "message": "Session not found"
            }), 404

         # Create response object
        response = {
            "status": "in_progress",
            "session_id": session.session_id,
            "has_rfid": session.rfid_tag is not None,
            "has_image": session.image_data is not None,
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.created_at)),
            "last_updated": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.last_updated))
        }
        # Add session type if available
        if hasattr(session, 'session_type'):
            if hasattr(session.session_type, 'value'):
                response["session_type"] = session.session_type.value
            else:
                response["session_type"] = str(session.session_type)

        return jsonify(response), 200

    except (ValueError, KeyError, AttributeError) as e:
        logger.error("[API] Error checking status: %s", str(e))
        return jsonify({"error": f"Error processing request: {str(e)}"}), 400
    except Exception as e:
        logger.error("[API] Unexpected error checking status: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500


# Function needed to get the image from the supabase database. for frontend to use
def get_image_from_storage(image_id, mock=False):
    # need to use the supabase client and the image_id to get the image from the storage bucket
    if mock:
        return "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"
    else:
        pass
    # Placeholder function to generate a random image
    return np.random.rand(128, 128, 3).tolist()
