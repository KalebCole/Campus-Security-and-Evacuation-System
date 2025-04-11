"""
Face recognition service API endpoints.
"""

import os
from flask import Blueprint, request, jsonify
import numpy as np
import base64
import cv2

from core.embedding import FaceEmbedding
from core.verification import FaceVerifier
from core.preprocessing import preprocess_image

# Initialize blueprint
face_recognition_routes = Blueprint('face_recognition', __name__)

# Initialize face recognition components
# Configure model path from environment variable or use default
# TODO: pull this from the config file in the config/paths.py
model_path = os.getenv(
    'MODEL_PATH', 'face_recognition/core/models/ghostfacenets.h5')
face_embedding = FaceEmbedding(model_path=model_path)
face_verifier = FaceVerifier()


@face_recognition_routes.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service status."""
    return jsonify({"status": "healthy"}), 200


@face_recognition_routes.route('/embed', methods=['POST'])
def generate_embedding():
    """Generate face embedding from an image."""
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({"error": "No image provided"}), 400

        # Decode base64 image
        image_data = base64.b64decode(data['image'])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Preprocess image
        preprocessed = preprocess_image(image)
        if preprocessed is None:
            return jsonify({"error": "Face not detected or image preprocessing failed"}), 400

        # Generate embedding
        embedding = face_embedding.generate_embedding(preprocessed)
        if embedding is None:
            return jsonify({"error": "Failed to generate embedding"}), 500

        return jsonify({
            "embedding": embedding.tolist()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@face_recognition_routes.route('/verify', methods=['POST'])
def verify_face():
    """Verify if two face embeddings belong to the same person."""
    try:
        data = request.json
        if not data or 'embedding1' not in data or 'embedding2' not in data:
            return jsonify({"error": "Missing embeddings"}), 400

        embedding1 = np.array(data['embedding1'])
        embedding2 = np.array(data['embedding2'])

        # Verify faces
        is_match, confidence = face_verifier.verify_faces(
            embedding1, embedding2)

        return jsonify({
            "is_match": bool(is_match),
            "confidence": float(confidence)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
