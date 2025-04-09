"""All routes for the campus security system."""
import logging
import numpy as np
import threading
import time
import cv2
from datetime import datetime
from flask import Blueprint, request, jsonify
import socket
import json

from app_config import Config
from model.model_integration import generate_embedding
from data.session import SessionType
from session_manager import SessionManager
from notifications.notification_service import NotificationService, NotificationType
from worker_manager import WorkerManager
from data.database import get_user_repository
from utils.similarity import calculate_similarity

# Configure logging
logger = logging.getLogger(__name__)

# Create the main routes blueprint
routes_bp = Blueprint('routes', __name__)

# Shared resources
notif_service = NotificationService()
session_manager = SessionManager()
worker_manager = WorkerManager(session_manager, notif_service)
user_repository = get_user_repository()

# Thread lock for thread-safe session access
session_lock = threading.Lock()

# System state
system_state = {
    "active": False,
    "last_activity": None
}

# Timeouts
SESSION_TIMEOUT = 15
SYSTEM_TIMEOUT = 15

# Allowed file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def verify_user(rfid_tag=None, image_data=None, embedding=None, session_id=None):
    """Unified verification logic that handles all verification scenarios."""
    try:
        # Get or create session
        session = session_manager.get_session(session_id)
        if not session:
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
            session_manager.update_session(
                session_id,
                rfid_tag=rfid_tag,
                session_type=SessionType.RFID_RECEIVED if not session.image_data else SessionType.VERIFICATION_COMPLETE
            )

            if not hasattr(session, 'user_data') or not session.user_data:
                user = user_repository.get_user_by_rfid(rfid_tag)
                if not user:
                    notif_service.send(NotificationType.RFID_NOT_FOUND, {
                        "rfid_tag": rfid_tag,
                        "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
                    })
                    return {
                        "status": "failure",
                        "message": "No user found for provided RFID",
                        "session_id": session_id
                    }, 404

                session_manager.update_session(session_id, user_data=user)
                notif_service.send(NotificationType.RFID_RECOGNIZED, {
                    "name": user['name'],
                    "rfid_tag": rfid_tag,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
                })

        # Handle image data input
        if image_data is not None:
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
            logger.info(
                f"[Logic] Session {session_id} has both RFID and image, ready for verification")
            return {
                "status": "processing",
                "message": "RFID and image received, processing verification",
                "session_id": session_id
            }, 202
        elif session.rfid_tag:
            return {
                "status": "pending_verification",
                "message": f"Suspected user: {session.user_data['name']}. Awaiting facial verification.",
                "session_id": session.session_id
            }, 202
        elif session.image_data:
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


# System Routes


@routes_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to check if the API is running."""
    return jsonify({"status": "success", "message": "API is running"}), 200


@routes_bp.route('/activate', methods=['GET'])
def activate_system():
    """Activate the security system and start the worker thread."""
    global system_state
    worker_manager.start_worker()
    system_state["active"] = True
    system_state["last_activity"] = time.time()
    logger.info("[System] Security system activated")
    return jsonify({
        "status": "success",
        "message": "System activated",
        "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
    }), 200


@routes_bp.route('/deactivate', methods=['GET'])
def deactivate_system():
    """Deactivate the security system and stop the worker thread."""
    global system_state
    worker_manager.stop_worker()
    system_state["active"] = False
    system_state["last_activity"] = None
    logger.info("[System] Security system deactivated")
    return jsonify({
        "status": "success",
        "message": "System deactivated",
        "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
    }), 200

# Verification Routes


@routes_bp.route('/rfid', methods=['POST'])
def handle_rfid():
    """Handle RFID tag input from the RFID client (Arduino)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        rfid_tag = data.get('rfid_tag')
        if not rfid_tag:
            return jsonify({"error": "No RFID tag provided"}), 400

        session_id = data.get('session_id')
        result, status_code = verify_user(
            rfid_tag=rfid_tag, session_id=session_id)
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"[API] Error processing RFID request: {str(e)}")
        return jsonify({"error": str(e)}), 500


@routes_bp.route('/image', methods=['POST'])
def handle_image():
    """Handle image input from the ESP32 camera client."""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            image_data = cv2.imdecode(
                np.frombuffer(file.read(), np.uint8),
                cv2.IMREAD_COLOR
            )
            session_id = request.form.get('session_id')
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
    """Get or create a session ID for the client."""
    if not system_state.get("active", False):
        return jsonify({
            "error": "System not activated",
            "message": "Please activate the system first"
        }), 400

    session = session_manager.create_session(SessionType.RFID_RECEIVED)
    return jsonify({
        "success": True,
        "session_id": session.session_id,
        "expires_in": SESSION_TIMEOUT
    }), 200


@routes_bp.route('/status/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """Get the status of a verification session."""
    session = session_manager.get_session(session_id)
    if not session:
        return jsonify({
            "error": "Session not found",
            "message": f"No session found with ID {session_id}"
        }), 404

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
