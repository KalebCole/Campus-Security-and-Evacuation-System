import base64
import cv2
from flask import Blueprint, request, jsonify
from supabase_client import supabase
from notifications.notifications import send_notification, send_sms_notification
from notifications.notification_service import NotificationService, NotificationType
import numpy as np
from config import Config
import uuid
import time
import uuid
import threading
from datetime import datetime
# Add the model directory
from model.model_integration import generate_embedding, perform_recognition


# =======================
# List of TODOs
# =======================
"""
# TODO: figure out timeout length
# TODO: Refactor this file to split the logic into separate files for the functions and the routes
# The files will be the following
# 1. routes.py - this file will contain the routes and the logic for the routes (examples: /rfid, /image, /embeddings)
# 2. db_operations.py - this file will contain the logic for the CRUD operations for the database and querying the database (examples: query_user_by_rfid, query_all_users)
# 3. verification_logic.py - this file will contain the logic for the verification process (examples: handle_rfid_and_image, handle_rfid_only, handle_embedding_only, process_verification)
# 4. input_handling.py - this file will contain the logic for handling the input data (examples: clean_stale_sessions, process_rfid_and_wait_for_embedding, monitor_sessions)
# 5. model_operations.py - this file will contain the logic for the model operations (examples: calculate_similarity, generate_embedding, everything in model_integartion.py)

# TODO: Create a session class to store the type of properties that are stored in the session_data dictionary
# this will allow for better type checking and easier to understand code

# TODO: Figure out how to have the clients have the same session_id for the same session
    # Clients are the following: ESP32, Web App, Arduino R4 Uno for RFID
    
# TODO: Add the logic for the server to send the unlock signal to the Arduino R4 Uno 

# TODO: What to do when face is not detected? should this trigger a new image to be taken before a timeout?


# TODO:
 Use Postman’s Collection Runner
Create a Collection:
Group all your endpoints (e.g., /rfid, /image, /verify, etc.) into a single collection.

Set Up Pre‑Requests & Tests:
You can write tests and pre‑request scripts in Postman to pass variables (like a session ID) from one request to the next.

Run the Collection:
Open the Collection Runner (click the "Runner" button in Postman) and run your collection. This will execute all the endpoints in sequence automatically, so you don’t have to press each one manually.

#TODO: Implement some wait feature for handle_rfid_and_image to wait if the session is in process of being updated
    example: receiving the rfid tag and then receiving the image before the rfid tag is processed
        what happens: the handle_rfid_only is called and then handle_rfid_and_image is called and it will perform the same db query twice
"""


# =======================
# Blueprint
# =======================

routes_bp = Blueprint('routes', __name__)
notif_service = NotificationService()


# Temporary session storage
session_data = {}
SESSION_TIMEOUT = 60  # 1 minute
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
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

# TODO: abstract this to a utility file


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# =======================
# Database Operations
# =======================


def query_user_by_rfid(rfid_tag, mock=False):
    """
    Query user by RFID tag from either mock database or actual database.

    :param rfid_tag: The RFID tag to search for.
    :param mock: Boolean flag to indicate whether to use the mock database.
    :return: User object if found, otherwise None.
    """
    if mock:
        print(f"[Mock DB] Searching for RFID {rfid_tag}")
        for user in mock_db:
            if user["rfid_tag"] == rfid_tag:
                print(f"[Mock DB] Found user for RFID {
                      rfid_tag}: {user['name']}")
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

# Case 1: RFID and Image both received

# Note: abstracted this to use dependency injection for the embed_func parameter


def handle_rfid_and_image(rfid_tag, image=None, embedding=None, session_id=None, embed_func=generate_embedding):
    # TODO: update this pydoc to match the rest of the codes pydocs
    """
    Handle verification when both RFID and image are available.

    Args:
        rfid_tag: The RFID tag to verify
        image: The image data for facial recognition
        embedding: The facial embedding for the image
        session_id: Optional session ID if this is part of an existing session

    Returns:
        dict: Response containing verification status and message
    """
    try:
        # Case 1: Check if we already have a session with this RFID
        if session_id and session_id in session_data:
            session = session_data[session_id]

            # If we already have an embedding from a previous image upload
            if "embedding" in session:
                embedding = session["embedding"]
            elif image:
                # Generate new embedding from the image
                embedding = embed_func(image)
                session["embedding"] = embedding

            # If we already queried the user data
            if "user_data" in session:
                user = session["user_data"]
            else:
                # Query user data from database
                user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
                if user:
                    session["user_data"] = user

        else:
            # No existing session, process both pieces fresh
            embedding = embed_func(image)
            user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)

            # Create new session if session_id provided
            if session_id:
                session_data[session_id] = {
                    "embedding": embedding,
                    "user_data": user if user else None,
                    "rfid": rfid_tag,
                    "timestamp": time.time()
                }

        # Verify the match
        if user:
            similarity = calculate_similarity(
                embedding, user["facial_embedding"])

            if user and similarity > 0.8:  # Threshold for matching
                notif_service.send(NotificationType.ACCESS_GRANTED, {
                    "name": user['name'],
                    "role": user.get("role", "N/A"),
                    "rfid_id": rfid_tag,
                    "session_id": session_id,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
                    "image_url": get_image_from_storage(user.get('photo_url'), mock=Config.MOCK_VALUE)
                })
                # TODO: Abstract this to a template
                return {
                    "status": "success",
                    "message": f"Access granted for {user['name']}.",
                    "similarity": similarity
                }
            else:
                notif_service.send(NotificationType.FACE_MISMATCH, {
                    "name": user['name'],
                    "rfid_id": rfid_tag,
                    "session_id": session_id,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
                    "db_image_url": get_image_from_storage(user.get('photo_url'), mock=Config.MOCK_VALUE),
                    # Replace with the actual URL sent from the client
                    "captured_image_url": get_image_from_storage(user.get('photo_url'), mock=Config.MOCK_VALUE),
                })
                return {
                    "status": "failure",
                    "message": "RFID and face mismatch.",
                    "similarity": similarity
                }
        else:
            notif_service.send(NotificationType.RFID_NOT_FOUND, {
                "rfid_id": rfid_tag,
                "session_id": session_id,
                "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
            })
            return {
                "status": "failure",
                "message": "No user found for provided RFID."
            }

    except Exception as e:
        print(f"Error in handle_rfid_and_image: {str(e)}")
        return {
            "status": "error",
            "message": f"Error processing verification: {str(e)}"
        }
    finally:
        # Clean up session if we have one
        if session_id and session_id in session_data:
            session_data.pop(session_id, None)

# Case 2: RFID received but no Image


def handle_rfid_only(rfid_tag, session_id=None):
    """
    Handle case when only RFID is received.

    Args:
        rfid_tag: The RFID tag to verify
        session_id: Optional session ID for tracking verification state

    Returns:
        dict: Response containing verification status and message
    """
    try:
        # check if the user is in the session already. if so, do not query the database again. instead, just exit
        if session_id and session_id in session_data:
            session = session_data[session_id]
            if "user_data" in session:
                return {
                    "status": "pending_verification",
                    "message": f"Suspected user: {session['user_data']['name']}. Awaiting facial verification.",
                    "session_id": session_id
                }
            else:
                user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
                if user:
                    session["user_data"] = user
                    
        else:
            user = session["user_data"]

        if user:
            # Create or update session data
            # TODO: check to see if this session is actually updated
            if session_id:
                session_data[session_id] = session_data.get(session_id, {})
                session_data[session_id].update({
                    'rfid': rfid_tag,
                    'user_data': user,  # Store user data to avoid re-querying later
                    'timestamp': time.time()
                })

            notif_service.send(NotificationType.RFID_RECOGNIZED, {
                "name": user['name'],
                "role": user.get("role", "N/A"),
                "rfid_id": rfid_tag,
                "session_id": session_id,
                "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
                "employee_image_url": get_image_from_storage(user.get('photo_url'), mock=Config.MOCK_VALUE)
            })

            return {
                "status": "pending_verification",
                "message": f"Suspected user: {user['name']}. Awaiting facial verification.",
                "session_id": session_id
            }
        else:
            # No user found - send critical notification
            notif_service.send(NotificationType.RFID_NOT_FOUND, {
                "rfid_id": rfid_tag,
                "session_id": session_id,
                "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
            })

            # Clean up session if it exists
            if session_id and session_id in session_data:
                session_data.pop(session_id, None)

            return {
                "status": "failure",
                "message": "No user found for provided RFID.",
                "session_id": None
            }

    except Exception as e:
        print(f"Error in handle_rfid_only: {str(e)}")
        # Clean up session if there's an error
        if session_id and session_id in session_data:
            session_data.pop(session_id, None)

        return {
            "status": "error",
            "message": f"Error processing RFID: {str(e)}",
            "session_id": None
        }

# Case 3: Image received but no RFID


# TODO: do we use this function? is it worth it to query the entire database for every image upload?
def handle_image_only(image_data, session_id=None, embed_func=generate_embedding):
    """
    params:
    image_data: The image data for facial recognition (jpeg)
    session_id: Optional session ID for tracking verification state


    Handle case when only image is received.
    """
    try:
        # check if the embedding is in the session already. if so, return
        # this is because right now, if the image is uploaded, the monitoring thread will continue to call this
        # function until the rfid is uploaded. this is to prevent the same image from being processed multiple times
        if session_id and session_id in session_data:
            session = session_data[session_id]
            if "embedding" in session:
                return {
                    "status": "pending_verification",
                    "message": "Awaiting RFID verification.",
                    "session_id": session_id
                }
        # Generate embedding from image
        embedding = embed_func(image_data)

        # Get all users and calculate similarities
        users = query_all_users(mock=Config.MOCK_VALUE)
        similarities = [
            {
                "user": user,
                "similarity": calculate_similarity(embedding, user['facial_embedding'])
            }
            for user in users
        ]

        # Get top 3 matches
        top_matches = sorted(
            similarities, key=lambda x: x['similarity'], reverse=True)[:3]

        # Format top matches for notification
        top_users = [
            f"{match['user']['name']} ({match['similarity']:.2f})"
            for match in top_matches
        ]

        # Update session if provided
        if session_id:
            session_data[session_id] = session_data.get(session_id, {})
            session_data[session_id].update({
                'embedding': embedding,
                'timestamp': time.time(),
                'top_matches': top_matches
            })
        # TODO: update the types of notifications in the notification object model
        notif_service.send(NotificationType.FACE_NOT_DETECTED, {
            "top_matches": top_users,
            "session_id": session_id,
            "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
        })

        return {
            "status": "pending_verification",
            "message": f"Top matches: {', '.join(top_users)}",
            "session_id": session_id
        }

    except Exception as e:
        print(f"Error in handle_image_only: {str(e)}")
        if session_id and session_id in session_data:
            session_data.pop(session_id, None)

        return {
            "status": "error",
            "message": f"Error processing image: {str(e)}",
            "session_id": None
        }
# =======================
# Session Monitoring
# =======================


def clean_stale_sessions():
    current_time = time.time()
    stale_sessions = [
        session_id for session_id, data in session_data.items()
        if current_time - data['timestamp'] > SESSION_TIMEOUT
    ]
    for session_id in stale_sessions:
        session_data.pop(session_id, None)
        print(f"[Monitor] Cleaned up stale session {session_id}")


def process_verification(session_id):
    """Process verification for a session"""
    if not session_id in session_data:
        return jsonify({"status": "error", "message": "Session not found"}), 404

    session = session_data[session_id]

    # If we have both pieces, handle verification
    if "rfid" in session and "embedding" in session:
        return handle_rfid_and_image(session["rfid"], session.get("image"), session_id)

    return jsonify({
        "status": "waiting_for_other_data",
        "session_id": session_id,
        "has_rfid": "rfid" in session,
        "has_embedding": "embedding" in session
    }), 202


def monitor_sessions():
    """Monitors active sessions and triggers appropriate verification processes."""
    while True:
        try:
            # TODO: Update this to use a queue for better performance
            current_time = time.time()
            for session_id, data in list(session_data.items()):
                # Case 1: RFID is available and embedding is generated
                if "embedding" in data and "rfid" in data:
                    threading.Thread(
                        target=handle_rfid_and_image,
                        args=(data["rfid"], data["embedding"],
                              session_id)
                    ).start()
                    # Remove session after processing
                    session_data.pop(session_id, None)
                # Case 2: Both RFID and image available
                elif "image" in data and "rfid" in data:
                    threading.Thread(
                        target=handle_rfid_and_image,
                        args=(data["rfid"], data.get("image"),
                              session_id)
                    ).start()
                    # Remove session after processing
                    session_data.pop(session_id, None)

                # Case 3: Only RFID
                elif "rfid" in data and "image" not in data:
                    threading.Thread(
                        target=handle_rfid_only,
                        args=(data["rfid"], session_id)
                    ).start()

                # Case 4: Only image
                elif "image" in data and "rfid" not in data:
                    threading.Thread(
                        target=handle_image_only,
                        args=(data["image"], session_id)
                    ).start()

                # Clean up expired sessions
                if current_time - data["timestamp"] > SESSION_TIMEOUT:
                    print(f"[Monitor] Session {
                          session_id} expired. Cleaning up.")
                    session_data.pop(session_id, None)

        except Exception as e:
            print(f"[Monitor] Error: {e}")
        time.sleep(1)


# Start monitor thread
threading.Thread(target=monitor_sessions, daemon=True).start()

# =======================
# Routes
# =======================

# route to test if we can access this blueprint


@routes_bp.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Routes Blueprint is working!"}), 200


@routes_bp.route('/verify', methods=['POST'])
def verify_access():
    data = request.get_json()
    rfid_tag = data.get('rfid_tag')
    image = data.get('image')
    session_id = data.get('session_id')

    result = handle_rfid_and_image(
        rfid_tag, image, session_id)
    return jsonify(result), 200 if result['status'] == 'success' else 403


@routes_bp.route('/rfid', methods=['POST'])
def receive_rfid():
    clean_stale_sessions()
    data = request.get_json()
    # TODO: validate rfid tag
    rfid_tag = data.get('rfid_tag')
    session_id = data.get('session_id', str(uuid.uuid4()))

    session_data[session_id] = session_data.get(session_id, {})
    session_data[session_id].update(
        {'rfid': rfid_tag, 'timestamp': time.time()})

    return jsonify({"status": "waiting_for_embedding", "session_id": session_id}), 202


@routes_bp.route("/image", methods=["POST"])
def receive_image():
    """Handles image upload from ESP32 CAM module."""
    clean_stale_sessions()

    # Key should match ESP32 code's "imageFile" name, not 'image'
    if 'imageFile' not in request.files:  # CHANGED FROM 'image'
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files['imageFile']  # CHANGED FROM 'image'
    session_id = request.form.get('session_id', str(uuid.uuid4()))

    try:
        if image_file.filename == '':
            return jsonify({"error": "Empty filename"}), 400

        if not allowed_file(image_file.filename):
            return jsonify({"error": "Invalid file type"}), 400

        image_bytes = image_file.read()
        image = cv2.imdecode(np.frombuffer(
            image_bytes, np.uint8), cv2.IMREAD_COLOR)

        session_data[session_id] = session_data.get(session_id, {})
        session_data[session_id].update({
            "image": image,
            "timestamp": time.time()
        })

        # check session to see if we have an RFID
        if "rfid" in session_data[session_id]:
            return jsonify({"status": "processing", "session_id": session_id}), 202
        else:
            return jsonify({"status": "waiting_for_rfid", "session_id": session_id}), 202

    except Exception as e:
        print(f"Error processing image: {e}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500


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
    return True, ""
