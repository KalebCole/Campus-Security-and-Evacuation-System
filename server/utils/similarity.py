"""
Similarity calculation utilities for face recognition.
"""
import numpy as np
from typing import List, Union, Any


def calculate_similarity(embedding1: Union[List[float], np.ndarray],
                         embedding2: Union[List[float], np.ndarray]) -> float:
    """
    Calculate cosine similarity between two facial embeddings.

    Args:
        embedding1: First embedding (128-dimensional)
        embedding2: Second embedding (128-dimensional)

    Returns:
        float: Cosine similarity between the embeddings (0-1)

    Raises:
        ValueError: If embeddings are not 128-dimensional
    """
    if len(embedding1) != 128 or len(embedding2) != 128:
        raise ValueError(
            f"Embeddings must be 128-dimensional. Got {len(embedding1)} and {len(embedding2)}")

    # Convert to numpy arrays if not already
    embedding1 = np.array(embedding1, dtype=np.float32)
    embedding2 = np.array(embedding2, dtype=np.float32)

    # Normalize embeddings
    embedding1 /= np.linalg.norm(embedding1)
    embedding2 /= np.linalg.norm(embedding2)

    # Calculate cosine similarity
    return float(np.dot(embedding1, embedding2))
