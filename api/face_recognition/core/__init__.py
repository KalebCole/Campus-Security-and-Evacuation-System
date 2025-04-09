"""
Core face recognition functionality using GhostFaceNets.

This package provides the fundamental components for face recognition:
- Preprocessing: Image normalization and alignment
- Embedding: Face embedding generation
- Verification: Face matching and identity verification
"""

from .preprocessing import preprocess_image
from .embedding import FaceEmbedding
from .verification import FaceVerifier

__all__ = ['preprocess_image', 'FaceEmbedding', 'FaceVerifier']
