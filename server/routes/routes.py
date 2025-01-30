import base64
import cv2
from flask import Blueprint, request, jsonify
from supabase_client import supabase
from utils.notifications import send_notification, send_sms_notification
import numpy as np
from config import Config
import uuid
import time
import uuid
import threading
# Add the model directory 
from model.model_integration import generate_embedding, perform_recognition


# TODO: figure out timeout length
# TODO: Refactor this file to split the logic into separate files for the functions and the routes
    # The files will be the following
        # 1. routes.py - this file will contain the routes and the logic for the routes (examples: /rfid, /image, /embeddings)
        # 2. db_operations.py - this file will contain the logic for the CRUD operations for the database and querying the database (examples: query_user_by_rfid, query_all_users)
        # 3. verification_logic.py - this file will contain the logic for the verification process (examples: handle_rfid_and_image, handle_rfid_only, handle_embedding_only, process_verification)
        # 4. input_handling.py - this file will contain the logic for handling the input data (examples: clean_stale_sessions, process_rfid_and_wait_for_embedding, monitor_sessions)
        # 5. model_operations.py - this file will contain the logic for the model operations (examples: calculate_similarity, generate_embedding, everything in model_integartion.py)
        


routes_bp = Blueprint('routes', __name__)
# Mocked recipient for notifications
NOTIFICATION_RECIPIENT = "+1234567890"
MOCK_VALUE = True

# Temporary session storage
session_data = {}
SESSION_TIMEOUT = 300  # 5 minutes
# TODO: abstract this timeout to the config file

# test endpoint for this blueprint


@routes_bp.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "This is a test endpoint for the routes blueprint"}), 200


# Mocked user data for testing
mock_db = [
    {"id": 1, "name": "Alice", "rfid_tag": "123456",
        "facial_embedding": [0.1] * 128},
    {"id": 2, "name": "Bob", "rfid_tag": "654321",
        "facial_embedding": [0.2] * 128},
    {"id": 3, "name": "Charlie", "rfid_tag": "789012",
        "facial_embedding": [0.3] * 128},
]


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
# Verification logic
# =======================

# Case 1: RFID and Image both received

# TODO: Create a function to handle both the rfid and the image
    # what happens when the entry is already queried from the db in the case when rfid is received and we are waiting on the image?
    # what happens when the embedding is already generated in the case when the image is received and we are waiting on the rfid?
def handle_rfid_and_image(rfid_tag, image):
    pass


# Case 2: RFID received but no Image
def handle_rfid_only(rfid_tag):
    user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
    if user:
        # TODO: verify if this is the correct notification that we want to send
        send_notification({
            "notification_type": "RFID_ACCESS_DENIED",
            "severity_level": "CRITICAL",
            "message": f"Possible unauthorized access by RFID {rfid_tag}. Suspected: {user['name']}.",
            "rfid_id": rfid_tag,
            "status": "Unread",
        })
        return {"status": "pending_verification", "message": f"Suspected user: {user['name']}. Verification required."}
    return {"status": "failure", "message": "No user found for provided RFID."}

# Case 3: Image received but no RFID

# TODO: Update this function to handle the image upload
    # It will do the following
    # 1. take in an image jpeg file
    # 2. generate the embedding from the image using the functions in the model_integration.py file
    # 3. query the db for all the users
    # 4. calculate the similarity between the embedding and the facial embeddings of all the users
    # 5. send a notification with the top 3 matches
def handle_embedding_only(embedding, perform_query=True):
    if perform_query:
        users = query_all_users(mock=Config.MOCK_VALUE)
        similarities = [
            {"user": user, "similarity": calculate_similarity(
                embedding, user['facial_embedding'])}
            for user in users
        ]
        similarities = sorted(
            similarities, key=lambda x: x['similarity'], reverse=True)[:3]
        top_users = [f"{similarity['user']['name']} (Similarity: {
            similarity['similarity']:.2f})" for similarity in similarities]
        send_notification({
            "notification_type": "FACE_NOT_RECOGNIZED",
            "severity_level": "CRITICAL",
            "message": f"Unknown face detected. Top matches: {', '.join(top_users)}.",
            "status": "Unread",
        })
        return {"status": "pending_verification", "message": f"Top matches: {', '.join(top_users)}"}
    else:
        send_notification({
            "notification_type": "FACE_NOT_RECOGNIZED",
            "severity_level": "CRITICAL",
            "message": "Unknown face detected. Immediate security verification required.",
            "status": "Unread",
        })
        return {"status": "failure", "message": "No RFID. Immediate security check triggered."}

# =======================
# Handling Input Data
# =======================


def clean_stale_sessions():
    current_time = time.time()
    stale_sessions = [
        session_id for session_id, data in session_data.items()
        if current_time - data['timestamp'] > SESSION_TIMEOUT
    ]
    for session_id in stale_sessions:
        session_data.pop(session_id, None)

# TODO: Update this function to handle the image upload
    # It will do the following
    # 1. get the current session 
    # 2. check 
def process_verification(session_id):
    """Processes verification once both RFID and embedding are received."""
    session = session_data.get(session_id, {})

    if "rfid" in session and "embedding" in session:
        user = query_user_by_rfid(session["rfid"])

        if user:
            similarity = calculate_similarity(
                session["embedding"], user["facial_embedding"])
            if similarity > 0.8:
                send_notification(
                    {
                        "notification_type": "RFID_ACCESS_GRANTED",
                        "severity_level": "INFO",
                        "message": f"Access granted for {user['name']}.",
                        "rfid_id": session['rfid'],
                        "face_id": user.get("id"),
                        "status": "Unread",
                    }
                )
                session_data.pop(session_id, None)
                return jsonify({"status": "success", "message": f"Access granted for {user['name']}."}), 200

        send_notification(
            {
                "notification_type": "RFID_ACCESS_DENIED",
                "severity_level": "CRITICAL",
                "message": "Access denied. RFID and face mismatch.",
                "rfid_id": session["rfid"],
                "status": "Unread",
            }
        )
        session_data.pop(session_id, None)
        return jsonify({"status": "failure", "message": "RFID and face mismatch."}), 403

    return jsonify({"status": "waiting_for_other_data", "session_id": session_id}), 202


def process_rfid_and_wait_for_embedding(session_id):
    """Triggers RFID lookup after image is received, then waits asynchronously for embedding."""
    session = session_data.get(session_id)
    if not session or "image" not in session:
        return

    print(f"[Monitor] Image received for session {
          session_id}. Querying RFID in DB...")

    # Query the user using RFID
    user = query_user_by_rfid(session["rfid"])

    if user:
        print(f"[Monitor] RFID found in DB. Waiting for embedding...")

        # Wait for embedding
        start_time = time.time()
        while time.time() - start_time < SESSION_TIMEOUT:
            if "embedding" in session_data.get(session_id, {}):
                print(
                    f"[Monitor] Embedding received! Proceeding with face verification.")
                return process_verification(session_id)
            time.sleep(0.5)

        # Timeout if embedding never arrives
        print(f"[Monitor] Embedding not received. Session {
              session_id} timed out.")
        session_data.pop(session_id, None)
    else:
        print(f"[Monitor] RFID not found in database. Session {
              session_id} expired.")
        session_data.pop(session_id, None)


def monitor_sessions():
    """Monitors active sessions and triggers the process when an image is received."""
    while True:
        try:
            current_time = time.time()
            for session_id, data in list(session_data.items()):
                # Case 1: Image and RFID both received
                    # if both have been received, then we query the db for the user and generate the embedding for the image
                if "image" in data and "rfid" in data and "embedding" not in data:
                    threading.Thread(
                        target=process_rfid_and_wait_for_embedding, args=(session_id,)).start()
                # Case 2: RFID received but no image
                    # if only the rfid has been received, then we query the db for the user and continue to wait for the image
                elif "rfid" in data and "embedding" not in data:
                    threading.Thread(
                        target=handle_rfid_only, args=(data["rfid"],)).start()
                # Case 3: Image received but no RFID
                    # if only the image has been received, we will generate the embedding, but continue to wait for the rfid
                elif "image" in data and "rfid" not in data:
                    # TODO: update this to use a method that handles the image upload, not the embedding
                    threading.Thread(
                        target=handle_embedding_only, args=(data["image"],)).start()
                # If session expires, clean it up
                if current_time - data["timestamp"] > SESSION_TIMEOUT:
                    print(f'''[Monitor] Session {
                          session_id} expired. Cleaning up.''')
                    session_data.pop(session_id, None)
        except Exception as e:
            print(f"[Monitor] Error: {e}")
        time.sleep(1)  # Poll every second


# Start the session monitor in the background
threading.Thread(target=monitor_sessions, daemon=True).start()


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


# TODO: remove this endpoint because we generate the embedding from the image
@routes_bp.route('/embeddings', methods=['POST'])
def receive_embedding():
    clean_stale_sessions()
    data = request.get_json()

   # Validate the facial_embedding field
    facial_embedding = data.get('facial_embedding')
    if not isinstance(facial_embedding, list) or len(facial_embedding) != 128:
        return jsonify({"error": f"Invalid 'facial_embedding' format. Must be a list of 128 floats. Got {len(facial_embedding)}"}), 400

    embedding = np.array(facial_embedding, dtype=np.float32)
    session_id = data.get('session_id', str(uuid.uuid4()))

    session_data[session_id] = session_data.get(session_id, {})
    session_data[session_id].update(
        {'embedding': embedding, 'timestamp': time.time()})

    return jsonify({"status": "waiting_for_rfid", "session_id": session_id}), 202


@routes_bp.route("/image", methods=["POST"])
def receive_image():
    """Receives an image, generates an embedding, and stores it in the session."""
    clean_stale_sessions()
    data = request.get_json()
    # TODO: update this to not use base64 decoding, instead it will be a file upload from the ESP32 CAM module. 
        # The image will be of the format Content-Type: multipart/form-data; boundary=dataMarker and it will be a jpeg
    image_data = data.get("base64_image")
    session_id = data.get("session_id", str(uuid.uuid4()))

    if not image_data:
        return jsonify({"error": "Image data is required"}), 400

    try:
        # TODO: Remove this decoding and use the image data directly
        image_bytes = base64.b64decode(image_data)
        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        # Generate embedding from image
        embedding = generate_embedding(image)

        session_data[session_id] = session_data.get(session_id, {})
        session_data[session_id].update(
            {"embedding": embedding, "timestamp": time.time()})

        return process_verification(session_id)

    except Exception as e:
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500


# =======================
# Handling Verification Results
# =======================


def handle_verification_result(result, session_id):
    severity = "INFO" if result['status'] == "success" else "CRITICAL"
    message = f"Verification Result: {result.get('reason', 'Access Granted')}"

    notification = {
        "notification_type": "RFID_ACCESS_GRANTED" if result['status'] == "success" else "RFID_ACCESS_DENIED",
        "severity_level": severity,
        "message": message,
        "rfid_id": session_data[session_id].get('rfid', None),
        "face_id": None,
        "status": "Unread",
    }

    # Send notifications
    send_notification(notification)
    # send_sms_notification(notification, phone_number=NOTIFICATION_RECIPIENT)

    # Clean up session
    session_data.pop(session_id, None)

# TODO: Implement these functions


# Function needed to get the image from the supabase database. for frontend to use
def get_image_from_supabase(image_id):
    # need to use the supabase client and the image_id to get the image from the storage bucket

    # Placeholder function to generate a random image
    return np.random.rand(128, 128, 3).tolist()

# Function needed to use the model to create an embedding from the image

# Function needed to send the embedding to the server


def send_embedding_to_server(embedding):
    # This will be used within some endpoint in the app to send the embedding to the server

    # Placeholder function to send the embedding to the server
    return True


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
