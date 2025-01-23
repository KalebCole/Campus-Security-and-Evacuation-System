from flask import Blueprint, request, jsonify
from supabase_client import supabase
from utils.helpers import validate_embedding, validate_rfid
import numpy as np
import uuid
import time


import json
import uuid
# TODO: use a python dictionary instead of redis to make development easier

verification_bp = Blueprint('verification', __name__)

# Temporary session storage
session_data = {}

# Mocked user data for testing
users = [
    {"id": 1, "name": "Alice", "rfid_tag": "123456", "facial_embedding": [0.1, 0.2, 0.3, 0.4, 0.5]},
    {"id": 2, "name": "Bob", "rfid_tag": "654321", "facial_embedding": [0.5, 0.4, 0.3, 0.2, 0.1]},
]

# Function to clean up stale sessions
def clean_stale_sessions(expiry_time=300):
    current_time = time.time()
    stale_sessions = [
        session_id for session_id, data in session_data.items()
        if current_time - data['timestamp'] > expiry_time
    ]
    for session_id in stale_sessions:
        session_data.pop(session_id, None)

# Verification logic
def verify_user(facial_embedding, rfid_tag):
    for user in users:
        stored_embedding = np.array(user['facial_embedding'], dtype=np.float32)
        stored_embedding /= np.linalg.norm(stored_embedding)  # Normalize stored embedding
        similarity = np.dot(facial_embedding, stored_embedding)  # Cosine similarity
        if similarity > 0.8 and user['rfid_tag'] == rfid_tag:
            return {"status": "success", "user_id": user['id'], "name": user['name']}
    return {"status": "failure", "reason": "No matching user found"}

@app.route('/embeddings', methods=['POST'])
def receive_embedding():
    clean_stale_sessions()  # Clean stale sessions before processing
    data = request.get_json()
    embedding = np.array(data.get('facial_embedding'), dtype=np.float32)
    session_id = data.get('session_id', str(uuid.uuid4()))  # Generate a session ID if not provided

    # Save embedding in session
    session_data[session_id] = session_data.get(session_id, {})
    session_data[session_id].update({'embedding': embedding, 'timestamp': time.time()})

    # Check if RFID is available
    if 'rfid' in session_data[session_id]:
        result = verify_user(session_data[session_id]['embedding'], session_data[session_id]['rfid'])
        session_data.pop(session_id)  # Clean up session after use
        return jsonify(result), 200

    return jsonify({"status": "waiting_for_rfid", "session_id": session_id}), 202

@app.route('/rfid', methods=['POST'])
def receive_rfid():
    clean_stale_sessions()  # Clean stale sessions before processing
    data = request.get_json()
    rfid_tag = data.get('rfid_tag')
    session_id = data.get('session_id', str(uuid.uuid4()))  # Generate a session ID if not provided

    # Save RFID in session
    session_data[session_id] = session_data.get(session_id, {})
    session_data[session_id].update({'rfid': rfid_tag, 'timestamp': time.time()})

    # Check if embedding is available
    if 'embedding' in session_data[session_id]:
        result = verify_user(session_data[session_id]['embedding'], session_data[session_id]['rfid'])
        session_data.pop(session_id)  # Clean up session after use
        return jsonify(result), 200

    return jsonify({"status": "waiting_for_embedding", "session_id": session_id}), 202

# TODO: Implement these functions

# Function needed to get the image from the supabase database
def get_image_from_supabase(image_id):
    # need to use the supabase client and the image_id to get the image from the storage bucket
    
    # Placeholder function to generate a random image
    return np.random.rand(128, 128, 3).tolist()

# Function needed to use the model to create an embedding from the image
def generate_embedding(image):
    # TODO: Need Thomas to upload the model and then import it as a package and use it here
    
    # Placeholder function to generate a random embedding
    return np.random.rand(128).tolist()


# Function needed to send the embedding to the server
def send_embedding_to_server(embedding):
    # This will be used within some endpoint in the app to send the embedding to the server
    
    # Placeholder function to send the embedding to the server
    return True




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
