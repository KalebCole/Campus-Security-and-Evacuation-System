"""
Face embedding generation using GhostFaceNets.
Handles model loading and embedding generation.
"""

import tensorflow as tf
import numpy as np
from typing import Optional
from .preprocessing import preprocess_image


class FaceEmbedding:
    def __init__(self, model_path: str):
        """
        Initialize the face embedding generator.

        Args:
            model_path: Path to the GhostFaceNets model
        """
        self.model = tf.keras.models.load_model(model_path)

    def generate_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Generate a face embedding from an image.

        Args:
            image: Preprocessed face image

        Returns:
            Face embedding vector or None if generation failed
        """
        try:
            # Preprocess image
            preprocessed = preprocess_image(image)
            if preprocessed is None:
                return None

            # Add batch dimension
            preprocessed = np.expand_dims(preprocessed, axis=0)

            # Generate embedding
            embedding = self.model.predict(preprocessed)

            # Normalize embedding
            # embedding = embedding / np.linalg.norm(embedding) # <-- Commented out based on GhostFaceNets recommendations

            return embedding[0]  # Remove batch dimension

        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return None
