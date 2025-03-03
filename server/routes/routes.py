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
from queue import Queue, Empty


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
# Blueprint
# =======================

routes_bp = Blueprint('routes', __name__)
notif_service = NotificationService()

# Initialize system state and session manager
system_state = {
    "active": False,
    "last_activity": None
}
session_manager = SessionManager()

# Temporary session storage
SESSION_TIMEOUT = 15  # 1 minute
SYSTEM_TIMEOUT = 15  # system timeout in seconds
# TODO: abstract this timeout to the config file


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
        msg = f"Embeddings must be 128-dimensional. Got {len(embedding1)} and {len(embedding2)}"
        raise ValueError(msg)
    embedding1 = np.array(embedding1, dtype=np.float32)
    embedding2 = np.array(embedding2, dtype=np.float32)
    embedding1 /= np.linalg.norm(embedding1)
    embedding2 /= np.linalg.norm(embedding2)
    return np.dot(embedding1, embedding2)

# =======================
# Logic to Handle the Inputs
# =======================


# Case 1: RFID and Image both received

# Note: abstracted this to use dependency injection for the embed_func parameter


def handle_rfid_and_image(rfid_tag, image=None, embedding=None, session_id=None, embed_func=generate_embedding):
    """Handle verification when both RFID and image are available."""
    try:
        session = session_manager.get_session(
            session_id) if session_id else None

        # Generate embedding if needed
        if not embedding and image:
            embedding = embed_func(image)

        # Get or update user data
        if session and session.user_data:
            user = session.user_data
        else:
            user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
            if session and user:
                session.add_user_data(user)

        # Verify match
        if user and embedding:
            similarity = calculate_similarity(
                embedding, user["facial_embedding"])

            if session:
                session.similarity_score = similarity

            if similarity > 0.8:
                if session:
                    session.update_verification_status("success", similarity)
                notif_service.send(NotificationType.ACCESS_GRANTED, {
                    "name": user['name'],
                    "role": user.get("role", "N/A"),
                    "rfid_id": rfid_tag,
                    "session_id": session_id,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
                    "similarity": similarity
                })
                return {"status": "success", "message": f"Access granted for {user['name']}", "similarity": similarity}
            else:
                if session:
                    session.update_verification_status("failure", similarity)
                # Send notification for mismatch
                notif_service.send(NotificationType.FACE_MISMATCH, {...})
                return {"status": "failure", "message": "RFID and face mismatch", "similarity": similarity}
        else:
            if session:
                session.update_verification_status("failure")
            notif_service.send(NotificationType.RFID_NOT_FOUND, {...})
            return {"status": "failure", "message": "No user found for provided RFID"}

    except Exception as e:
        logger.error(f"Error in handle_rfid_and_image: {str(e)}")
        return {"status": "error", "message": f"Error processing verification: {str(e)}"}


def handle_rfid_only(rfid_tag, session_id=None):
    """Handle RFID-only verification"""
    try:
        # Get or create session
        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(SessionType.RFID_RECEIVED)
            session_id = session.session_id

        # Check if we already have user data
        if not session.user_data:
            user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
            if user:
                session.add_user_data(user)
                session.rfid_tag = rfid_tag
            else:
                session_manager.remove_session(session.session_id)
                return {
                    "status": "failure",
                    "message": "No user found for provided RFID",
                    "session_id": None
                }

        return {
            "status": "pending_verification",
            "message": f"Suspected user: {session.user_data['name']}. Awaiting facial verification.",
            "session_id": session.session_id
        }

    except Exception as e:
        logger.error(f"Error in handle_rfid_only: {str(e)}")
        if session_id:
            session_manager.remove_session(session_id)
        return {"status": "error", "message": str(e)}


def handle_image_only(image_data, session_id=None, embed_func=generate_embedding):
    """Handle image-only verification"""
    try:
        # Get or create session
        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(
                SessionType.IMAGE_RECEIVED)
            session_id = session.session_id

        # Generate embedding
        embedding = embed_func(image_data)
        session.embedding = embedding
        session.image_data = image_data

        # TODO: Fix this to where we do not need to query all users. Will this be a problem if we have a large number of users?

        # Find potential matches
        users = query_all_users(mock=Config.MOCK_VALUE)
        similarities = [
            {"user": user, "similarity": calculate_similarity(
                embedding, user['facial_embedding'])}
            for user in users
        ]

        # Store top matches
        top_matches = sorted(
            similarities, key=lambda x: x['similarity'], reverse=True)[:3]
        session.add_top_matches(top_matches)

        return {
            "status": "pending_verification",
            "message": "Image processed, awaiting RFID",
            "session_id": session.session_id
        }

    except Exception as e:
        logger.error(f"Error in handle_image_only: {str(e)}")
        if session_id:
            session_manager.remove_session(session_id)
        return {"status": "error", "message": str(e)}

# =======================
# Session Monitoring
# =======================


def clean_stale_sessions():
    """Clean up sessions that have exceeded the timeout period"""
    try:
        current_time = time.time()
        stale_sessions = []

        # Get all active sessions from session manager
        active_sessions = session_manager.get_all_sessions()

        for session_id, session in active_sessions.items():
            # Check if session has exceeded timeout
            age = current_time - session.last_updated
            if age > SESSION_TIMEOUT:
                stale_sessions.append(session_id)
                logger.info(
                    f"[Session Cleanup] Marking session {session_id} as stale. Age: {age:.2f}s"
                )

        # Remove stale sessions
        for session_id in stale_sessions:
            session_manager.remove_session(session_id)
            logger.info(
                f"[Session Cleanup] Removed stale session {session_id}")

        if stale_sessions:
            logger.info(
                f"[Session Cleanup] Cleaned {len(stale_sessions)} stale sessions")

    except Exception as e:
        logger.error(
            f"[Session Cleanup] Error cleaning stale sessions: {str(e)}")


verification_queue = Queue()


def check_system_timeout():
    """Check if system should be deactivated due to timeout"""
    if system_state["active"] and system_state["last_activity"]:
        current_time = time.time()
        time_since_last_activity = current_time - system_state["last_activity"]
        logger.debug(
            f"[System] Time since last activity: {time_since_last_activity:.2f}s")

        if time_since_last_activity > SYSTEM_TIMEOUT:
            system_state["active"] = False
            system_state["last_activity"] = None
            logger.info(
                f"[System] System deactivated due to timeout after {time_since_last_activity:.2f}s of inactivity")
            return True
    return False


def verification_worker():
    """Worker thread that processes verification requests from queue"""
    last_timeout_check = time.time()
    TIMEOUT_CHECK_INTERVAL = 1.0  # Check timeout every second

    while True:
        try:
            current_time = time.time()

            # Check timeout periodically
            if current_time - last_timeout_check >= TIMEOUT_CHECK_INTERVAL:
                check_system_timeout()
                last_timeout_check = current_time

            # Try to get a request with timeout
            try:
                request = verification_queue.get(timeout=1.0)
            except Empty:
                # No request available, continue to next iteration
                continue

            # Only process requests if system is active
            if not system_state["active"]:
                logger.warning("[Worker] Skipping request - system inactive")
                verification_queue.task_done()  # Must call task_done() for each get()
                continue

            # Update last activity timestamp
            system_state["last_activity"] = time.time()
            logger.debug(
                f"[System] Updated last activity: {system_state['last_activity']}")

            # Process based on request type
            try:
                if request.type == VerificationType.RFID_AND_IMAGE:
                    session = session_manager.get_session(request.session_id)
                    if session:
                        handle_rfid_and_image(
                            request.rfid_tag,
                            request.image_data,
                            request.embedding,
                            request.session_id
                        )
                elif request.type == VerificationType.RFID_ONLY:
                    handle_rfid_only(request.rfid_tag, request.session_id)
                elif request.type == VerificationType.IMAGE_ONLY:
                    handle_image_only(request.image_data, request.session_id)
            finally:
                # Ensure task_done() is called exactly once per get()
                verification_queue.task_done()

        except Exception as e:
            logger.error(f"[Verification Worker] Error: {e}")
            # Don't call task_done() here as we either already called it or didn't get an item
        finally:
            time.sleep(0.1)  # Prevent CPU spinning


# Should this thread be running all the time?
# TODO: should this be running only when the system is active?
    # if so, how do we start and stop this thread?
    # do we need to have a separate thread for this?
# Start worker thread
threading.Thread(target=verification_worker, daemon=True).start()

# =======================
# Routes
# =======================

# route to test if we can access this blueprint


@routes_bp.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Routes Blueprint is working!"}), 200


@routes_bp.route('/activate', methods=['GET'])  # Changed from /activate
def activate_system():
    """Activate the system"""
    system_state["active"] = True
    system_state["last_activity"] = time.time()
    logger.info(f"[System] System activated. State: {system_state}")
    return jsonify({"status": "success", "message": "System activated"}), 200


# Changed from /deactivate
@routes_bp.route('/deactivate', methods=['GET'])
def deactivate_system():
    """Deactivate the system"""
    system_state["active"] = False
    system_state["last_activity"] = None
    logger.info(f"[System] System manually deactivated. State: {system_state}")
    return jsonify({"status": "success", "message": "System deactivated"}), 200


@routes_bp.route('/verify', methods=['POST'])
def verify_access():
    try:
        data = request.get_json()
        rfid_tag = data.get('rfid_tag')
        image = data.get('image')
        session_id = data.get('session_id')

        if not rfid_tag:
            return jsonify({"error": "RFID tag is required"}), 400

        # Queue the verification request
        verification_queue.put(VerificationRequest(
            type=VerificationType.RFID_AND_IMAGE,
            session_id=session_id,
            rfid_tag=rfid_tag,
            image_data=image
        ))

        return jsonify({
            "status": "processing",
            "session_id": session_id
        }), 202

    except Exception as e:
        logger.error(f"[API] Error in verify_access: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@routes_bp.route('/image', methods=['POST'])
def receive_image():
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

        # Get or create session
        session = session_manager.get_session(session_id)
        logger.debug(f"[API] Session found: {session is not None}")
        if not session:
            session = session_manager.create_session(
                SessionType.IMAGE_RECEIVED)
            session_id = session.session_id

        # Update session with image data
        session_manager.update_session(
            session_id,
            image_data=image,
            session_type=SessionType.IMAGE_RECEIVED
        )

        # Only queue verification if we have both RFID and user data
        if session.has_rfid() and hasattr(session, 'user_data'):
            logger.info(
                "[API] Session has RFID and user data, queueing full verification")
            verification_queue.put(VerificationRequest(
                type=VerificationType.RFID_AND_IMAGE,
                session_id=session_id,
                rfid_tag=session.rfid_tag,
                image_data=image
            ))
            return jsonify({
                "status": "processing",
                "session_id": session_id
            }), 202
        # TODO: queue when we have image only
        else:
            logger.info("[API] Waiting for RFID verification")
            return jsonify({
                "status": "waiting_for_rfid",
                "session_id": session_id
            }), 202

    except Exception as e:
        logger.error(f"[API] Error processing image: {str(e)}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500


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

        return jsonify({
            "status": "in_progress",
            "session_type": session.session_type.value,
            "has_rfid": session.has_rfid(),
            "has_image": session.has_image(),
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.created_at)),
            "last_updated": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.last_updated))
        }), 200

    except Exception as e:
        logger.error(f"[API] Error checking status: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Route to handle RFID data from the Mega


@routes_bp.route('/rfid', methods=['POST'])
def receive_rfid():
    """Handle RFID data from the Arduino Mega"""
    logger.info("[API] Received RFID request")

    check_system_timeout()

    if not system_state["active"]:
        logger.warning("[System] Received RFID while system inactive")
        return jsonify({
            "status": "error",
            "message": "System not activated"
        }), 400

    try:
        data = request.get_json()
        rfid_tag = data.get('rfid_tag')
        session_id = data.get('session_id', str(uuid.uuid4()))
        logger.info(f"[API] Processing RFID data: {rfid_tag}")

        # Get or create session first
        session = session_manager.get_session(session_id)
        if not session:
            session = session_manager.create_session(SessionType.RFID_RECEIVED)
            session_id = session.session_id

        # Store RFID in session immediately
        session_manager.update_session(
            session_id,
            rfid_tag=rfid_tag,
            session_type=SessionType.RFID_RECEIVED
        )

        # Query user data
        user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
        if not user:
            return jsonify({
                "status": "failure",
                "message": "No user found for provided RFID",
                "session_id": session_id
            }), 404

        # Store user data in session
        session_manager.update_session(
            session_id,
            user_data=user
        )

        # Check if we already have an image
        if session.has_image():
            logger.info(
                "[API] Session already has image, queueing full verification")
            verification_queue.put(VerificationRequest(
                type=VerificationType.RFID_AND_IMAGE,
                session_id=session_id,
                rfid_tag=rfid_tag,
                image_data=session.image_data
            ))
        else:
            logger.info("[API] No image yet, waiting for image")

        return jsonify({
            "status": "processing",
            "message": "RFID processed, waiting for image verification",
            "session_id": session_id
        }), 202

    except Exception as e:
        logger.error(f"[API] Error processing RFID: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to process RFID: {str(e)}"
        }), 500

# TODO: Implement these functions


# Function needed to get the image from the supabase database. for frontend to use
def get_image_from_storage(image_id, mock=False):
    # need to use the supabase client and the image_id to get the image from the storage bucket
    if mock:
        return "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"
    else:
        pass
    # Placeholder function to generate a random image
    return np.random.rand(128, 128, 3).tolist()

# ========================

# Supabase tables and storage
# user_table = supabase.table(app.config['SUPABASE_USER_TABLE'])
# storage_bucket = supabase.storage.get_bucket(
#     app.config['SUPABASE_STORAGE_BUCKET'])
# user_entries_storage_path = app.config['SUPABASE_USER_ENTRIES_STORAGE_PATH']

# ========================
# CRUD Operations for the Supabase DB
# Includes:
# FRONTEND
# - Create a new user
# - Get all users
# - Get a single user by ID
# - Update a user by ID
# - Delete a user by ID

# @routes_bp.route('/upload-image', methods=['POST'])
# def upload_image():

#     data = request.get_json()
#     # validate the request
#     if not data:
#         return jsonify({"error": "No data provided"}), 400

#     # validate the image data
#     if 'base64_image' not in data:
#         return jsonify({"error": "No image provided"}), 400

#     # Extract the image data from the POST request
#     image_data = data.get('base64_image')
#     if image_data:
#         # Decode the base64-encoded image
#         image_bytes = base64.b64decode(image_data)

#         # Generate a unique file name or use a provided one
#         unique_filename = str(uuid.uuid4()) + '.jpg'
#         path_on_supastorage = f'{user_entries_storage_path}/{unique_filename}'

#         # Upload the image bytes to Supabase storage
#         response = storage_bucket.upload(
#             path=path_on_supastorage, file=image_bytes, file_options={"content-type": "image/jpeg"})

#         # Check if the image was uploaded successfully
#         if response.status_code != 200:
#             return jsonify({"error": "Failed to upload image"}), 500

#         # fetch from the storage
#         image_url = storage_bucket.get_public_url(path_on_supastorage)
#         print(image_url)

#         # validate the response
#         if not image_url:
#             return jsonify({"error": "Failed to get image url"}), 500

#         # insert the user into the table
#         user = {"photo_url": image_url}
#         response = user_table.insert(user).execute()
#         print(response)

#         # validate the response
#         if not response:
#             return jsonify({"error": "Failed to insert user"}), 500

#         return jsonify({"message": "Image received successfully"}), 200
#     else:
#         return jsonify({"error": "No image provided"}), 400


# @routes_bp.route('/get-users', methods=['GET'])
# def get_users():
#     # Query the 'users' table in Supabase
#     response = user_table.select('*').execute()

#     # Print the response for debugging
#     print("in get users")
#     print(response)
#     # response data
#     print("response data: " + str(response.data))

#     print("json response data" + str(jsonify(response.data)))

#     # Return the data portion of the response
#     if response.data:
#         return jsonify(response.data), 200
#     else:
#         return jsonify({"error": "No data found"}), 404


# VALIDATION LOGIC

# Used to validate the 'base64_image' field in the request payload
def validate_embedding(embedding):
    if not isinstance(embedding, list) or len(embedding) != 128:
        return False, "Invalid 'facial_embedding' format. Must be a list of 128 floats."
    if not all(isinstance(x, (float, int)) for x in embedding):
        return False, "'facial_embedding' must contain numeric values."
    return True, ""

# Used to validate the 'rfid_tag' field in the request payload


def validate_rfid(rfid_tag):
    if not isinstance(rfid_tag, str):
        return False, "Invalid 'rfid_tag' format. Must be a string."
        return False, "Invalid 'rfid_tag' format. Must be a string."
    return True, ""
