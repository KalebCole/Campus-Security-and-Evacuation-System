"""
Face embedding generation using GhostFaceNets.
Handles model loading and embedding generation.
"""

import tensorflow as tf
import numpy as np
from typing import Optional
# Updated import to include new functions
from .preprocessing import detect_face, align_face_simple, preprocess_image
import logging

logger = logging.getLogger(__name__)  # Add logger


class FaceEmbedding:
    def __init__(self, model_path: str):
        """
        Initialize the face embedding generator.

        Args:
            model_path: Path to the GhostFaceNets model
        """
        # TODO: Add error handling for model loading?
        self.model = tf.keras.models.load_model(model_path)
        logger.info(f"Loaded face embedding model from {model_path}")

    def generate_embedding(self, raw_image: np.ndarray) -> Optional[np.ndarray]:
        """
        Generate a face embedding from a raw input image.
        Performs detection, alignment (simple crop), and preprocessing.

        Args:
            raw_image: Raw input image (BGR format from OpenCV decode).

        Returns:
            Face embedding vector (numpy array) or None if any step failed.
        """
        logger.debug("Starting embedding generation process...")
        try:
            # 1. Detect Face
            logger.debug("Step 1: Detecting face...")
            bounding_box = detect_face(raw_image)
            if bounding_box is None:
                logger.warning(
                    "Face detection failed. Cannot generate embedding.")
                return None
            logger.debug(f"Face detected with box: {bounding_box}")

            # 2. Align Face (Simple Crop)
            logger.debug("Step 2: Aligning face (simple crop)...")
            aligned_face = align_face_simple(raw_image, bounding_box)
            if aligned_face is None:
                logger.warning(
                    "Face alignment (cropping) failed. Cannot generate embedding.")
                return None
            logger.debug(
                f"Face cropped successfully. Shape: {aligned_face.shape}")

            # 3. Preprocess Aligned Face (BGR->RGB, Resize, Normalize)
            logger.debug("Step 3: Preprocessing cropped face...")
            preprocessed_face = preprocess_image(aligned_face)
            if preprocessed_face is None:
                logger.warning(
                    "Final face preprocessing failed. Cannot generate embedding.")
                return None
            logger.debug(
                f"Face preprocessed successfully. Shape: {preprocessed_face.shape}")

            # 4. Add Batch Dimension
            logger.debug("Step 4: Adding batch dimension...")
            batch_input = np.expand_dims(preprocessed_face, axis=0)
            logger.debug(f"Final input shape for model: {batch_input.shape}")

            # 5. Generate Embedding using the Model
            logger.debug("Step 5: Generating embedding via model.predict...")
            embedding = self.model.predict(batch_input)
            logger.debug(f"Raw embedding generated. Shape: {embedding.shape}")

            # 6. Remove Batch Dimension & Return
            # Note: Redundant L2 normalization is already commented out
            final_embedding = embedding[0]
            logger.info(
                f"Embedding generated successfully. Final shape: {final_embedding.shape}")
            return final_embedding

        except Exception as e:
            logger.error(
                f"Error during embedding generation pipeline: {e}", exc_info=True)
            return None
