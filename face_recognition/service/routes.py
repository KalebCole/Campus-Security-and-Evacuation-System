"""
Face recognition service API endpoints.
"""

import os
from flask import Blueprint, request, jsonify
import numpy as np
import base64
import cv2
import logging

from core.embedding import FaceEmbedding
from core.verification import FaceVerifier
from core.preprocessing import preprocess_image

# Initialize blueprint
face_recognition_routes = Blueprint('face_recognition', __name__)

# Setup logger for this blueprint
logger = logging.getLogger(__name__)

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
    logger.info("Received request for /embed")
    try:
        data = request.json
        logger.debug(
            f"Request JSON data keys: {list(data.keys()) if data else 'None'}")
        if not data or 'image' not in data:
            logger.warning(
                "Request rejected: No JSON data or 'image' key missing.")
            return jsonify({"error": "No image provided"}), 400

        # Decode base64 image
        logger.debug("Attempting Base64 decode...")
        image_data = base64.b64decode(data['image'])
        logger.info(f"Base64 decoded successfully, {len(image_data)} bytes.")

        logger.debug("Attempting cv2.imdecode...")
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            logger.error(
                "cv2.imdecode failed. Input data might not be a valid image format.")
            return jsonify({"error": "Failed to decode image data"}), 400
        logger.info(f"cv2.imdecode successful. Image shape: {image.shape}")

        # Preprocess image
        logger.debug("Attempting preprocess_image...")
        preprocessed = preprocess_image(image)
        if preprocessed is None:
            logger.warning(
                "preprocess_image returned None. Face not detected or preprocessing failed.")
            return jsonify({"error": "Face not detected or image preprocessing failed"}), 400
        logger.info(
            f"preprocess_image successful. Preprocessed shape: {preprocessed.shape}")

        # Generate embedding
        logger.debug("Attempting generate_embedding...")
        embedding = face_embedding.generate_embedding(preprocessed)
        if embedding is None:
            logger.error("generate_embedding returned None.")
            return jsonify({"error": "Failed to generate embedding"}), 500
        logger.info(
            f"generate_embedding successful. Embedding dimensions: {embedding.shape}")

        return jsonify({
            "embedding": embedding.tolist()
        }), 200

    except base64.binascii.Error as b64_error:
        logger.error(f"Base64 decoding error: {b64_error}", exc_info=True)
        return jsonify({"error": f"Invalid Base64 data: {b64_error}"}), 400
    except Exception as e:
        logger.error(f"Unexpected error in /embed: {e}", exc_info=True)
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
