from flask import Blueprint, request, jsonify
from supabase_client import supabase
from utils.helpers import validate_embedding, validate_rfid
import numpy as np
import redis
import json
import uuid

verification_bp = Blueprint('verification', __name__)

# Initialize Redis client
r = redis.Redis(host='localhost', port=6379, db=0)


def verify_user(facial_embedding, rfid_tag):
    # TODO: Do we need to normalize the facial embeddings before comparing? or is it already normalized?
    # Normalize the facial embedding
    # embedding = np.array(facial_embedding, dtype=np.float32)
    # embedding /= np.linalg.norm(embedding)

    # Using in memory data for demonstration
    users = [
        {
            "id": 1,
            "name": "Alice",
            "rfid_tag": "123456",
            "facial_embedding": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        },
        {
            "id": 2,
            "name": "Bob",
            "rfid_tag": "654321",
            "facial_embedding": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1]
        },
        {
            "id": 3,
            "name": "Charlie",
            "rfid_tag": "987654",
            "facial_embedding": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.1, 0.2]
        }
    ]

    # TODO: implement this with supabase
    # Fetch all users from the database
    # response = supabase.table('users').select('*').execute()
    # users = response.data

    for user in users:
        # TODO: implement a better way to compare facial embeddings
            # can we send the embeddings to the db and filter from there?
            # or should we compare the embeddings here? 
        stored_embedding = np.array(user['facial_embedding'], dtype=np.float32)
        stored_embedding /= np.linalg.norm(stored_embedding)
        similarity = np.dot(facial_embedding, stored_embedding)
        # TODO: implement a better threshold for facial similarity
        if similarity > 0.8:  # Threshold for facial similarity
            if user['rfid_tag'] == rfid_tag:
                return {"status": "success", "user_id": user['id'], "name": user['name']}
    return {"status": "failure", "reason": "No matching user found"}


@verification_bp.route('/embeddings', methods=['POST'])
def receive_embedding():
    data = request.get_json()
    embedding = data.get('facial_embedding')
    session_id = data.get('session_id')  # Optional: Provided by client

    # debug
    print("INSIDE RECEIVE EMBEDDING")
    print("embedding: " + str(embedding))
    print("session_id: " + str(session_id))

    is_valid, message = validate_embedding(embedding)
    if not is_valid:
        return jsonify({"status": "error", "message": message}), 400

    if not session_id:
        # Generate a new session ID if not provided
        session_id = str(uuid.uuid4())

    # Store the embedding in Redis with session_id
    r.hset(session_id, 'embedding', json.dumps(embedding))
    r.expire(session_id, 60)  # Set a timeout of 60 seconds

    # Check if RFID data is already received
    rfid_data = r.hget(session_id, 'rfid_tag')
    if rfid_data:
        r.delete(session_id)
        result = verify_user(embedding, rfid_data.decode('utf-8'))
        return jsonify(result), 200

    return jsonify({"status": "waiting_for_rfid", "session_id": session_id}), 202


@verification_bp.route('/rfid', methods=['POST'])
def receive_rfid():
    data = request.get_json()
    rfid_tag = data.get('rfid_tag')
    session_id = data.get('session_id')  # Optional: Provided by client

    # debug
    print("INSIDE RECEIVE RFID")
    print("rfid_tag: " + str(rfid_tag))
    print("session_id: " + str(session_id))

    # is_valid, message = validate_rfid(rfid_tag)
    # if not is_valid:
    #     return jsonify({"status": "error", "message": message}), 400

    # if not session_id:
    #     # Generate a new session ID if not provided
    #     session_id = str(uuid.uuid4())

    # # Store the RFID tag in Redis with session_id
    # r.hset(session_id, 'rfid_tag', rfid_tag)
    # r.expire(session_id, 60)  # Set a timeout of 60 seconds

    # # Check if embedding data is already received
    # embedding_data = r.hget(session_id, 'embedding')
    # if embedding_data:
    #     embedding = json.loads(embedding_data.decode('utf-8'))
    #     r.delete(session_id)
    #     result = verify_user(embedding, rfid_tag)
    #     return jsonify(result), 200

    return jsonify({"status": "waiting_for_embedding", "session_id": session_id}), 202
