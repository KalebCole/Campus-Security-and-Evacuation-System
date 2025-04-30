"""
Face verification utilities.
Handles face matching and verification logic.
"""

import numpy as np


class FaceVerifier:
    def __init__(self, threshold=0.6):
        """
        Initialize the face verifier.

        Args:
            threshold: Similarity threshold for verification
        """
        self.threshold = threshold

    def verify_faces(self, embedding1, embedding2):
        """
        Verify if two face embeddings belong to the same person.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding

        Returns:
            tuple: (is_match, similarity_score)
        """
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2)

        # Determine if it's a match
        is_match = similarity >= self.threshold

        return is_match, similarity

    def verify(self, embedding1, embedding2):
        """
        Backward compatible method for verification.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding

        Returns:
            bool: True if the faces match, False otherwise
        """
        is_match, _ = self.verify_faces(embedding1, embedding2)
        return is_match
