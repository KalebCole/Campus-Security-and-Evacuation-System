from flask import Blueprint, request, jsonify
from supabase_client import supabase
from utils.notifications import send_notification, send_sms_notification
import numpy as np
from config import Config
import uuid
import time
import uuid
import threading
from model.model_integration import generate_embedding  # Import embedding function


# TODO: figure out timeout length


routes_bp = Blueprint('routes', __name__)
# Mocked recipient for notifications
NOTIFICATION_RECIPIENT = "+1234567890"
MOCK_VALUE = True

# Temporary session storage
session_data = {}

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

# Case 1: RFID and embedding both received

def handle_rfid_and_embedding(rfid_tag, embedding):
    user = query_user_by_rfid(rfid_tag, mock=True)
    if user:
        similarity = calculate_similarity(embedding, user['facial_embedding'])
        if similarity > 0.8:
            send_notification({
                "notification_type": "RFID_ACCESS_GRANTED",
                "severity_level": "INFO",
                "message": f"Access granted for {user['name']}.",
                "rfid_id": rfid_tag,
                "face_id": user.get('id'),
                "status": "Unread",
            })
            return {"status": "success", "message": f"Access granted for {user['name']}."}
    send_notification({
        "notification_type": "RFID_ACCESS_DENIED",
        "severity_level": "CRITICAL",
        "message": "Access denied. RFID and embedding mismatch.",
        "rfid_id": rfid_tag,
        "status": "Unread",
    })
    return {"status": "failure", "message": "RFID and embedding mismatch."}

# Case 2: RFID received but no embedding


def handle_rfid_only(rfid_tag):
    user = query_user_by_rfid(rfid_tag, mock=Config.MOCK_VALUE)
    if user:
        send_notification({
            "notification_type": "RFID_ACCESS_DENIED",
            "severity_level": "CRITICAL",
            "message": f"Possible unauthorized access by RFID {rfid_tag}. Suspected: {user['name']}.",
            "rfid_id": rfid_tag,
            "status": "Unread",
        })
        return {"status": "pending_verification", "message": f"Suspected user: {user['name']}. Verification required."}
    return {"status": "failure", "message": "No user found for provided RFID."}

# Case 3: Embedding received but no RFID


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


SESSION_TIMEOUT = 300  # 5 minutes


def monitor_sessions():
    while True:
        try:
            current_time = time.time()
            for session_id, data in list(session_data.items()):
                # Handle complete sessions
                if 'rfid' in data and 'embedding' in data:
                    print(f"[Monitor] Complete session: {session_id}")
                    handle_rfid_and_embedding(data['rfid'], data['embedding'])
                    session_data.pop(session_id, None)
                    continue

                # Timeout handling
                if current_time - data['timestamp'] > SESSION_TIMEOUT:
                    if 'rfid' in data:
                        print(
                            f"[Monitor] Timeout for RFID-only session: {session_id}")
                        handle_rfid_only(data['rfid'])
                    elif 'embedding' in data:
                        print(
                            f"[Monitor] Timeout for Embedding-only session: {session_id}")
                        handle_embedding_only(data['embedding'])
                    else:
                        print(f"[Monitor] Timeout for empty session: {
                              session_id}")
                    session_data.pop(session_id, None)
                    continue

        except Exception as e:
            print(f"Error in monitor_sessions: {e}")
        time.sleep(0.1)  # Poll every 100ms


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


# Function needed to get the image from the supabase database
def get_image_from_supabase(image_id):
    # need to use the supabase client and the image_id to get the image from the storage bucket

    # Placeholder function to generate a random image
    return np.random.rand(128, 128, 3).tolist()

# Function needed to use the model to create an embedding from the image


def generate_embedding(image):
    # TODO: Need Thomas to upload the model and then import it as a package and use it here
    # Paths to the test images
    # esp32_image = r'model\image.png'
    # db_image = r'model\image2.png'
    # model_integration.perform_recognition(esp32_image, db_image)
    # Placeholder function to generate a random embedding
    return np.random.rand(128).tolist()


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
