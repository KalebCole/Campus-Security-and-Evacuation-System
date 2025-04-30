"""
Face recognition system package.

This package provides face recognition functionality for the Campus Security and Evacuation System.
The package is organized into submodules for core functionality, service implementation, 
configuration, and tests.
"""

# Core functionality
from .core.preprocessing import preprocess_image
from .core.embedding import FaceEmbedding
from .core.verification import FaceVerifier

# Configuration
from .config.model_config import (
    MODEL_INPUT_SIZE,
    MODEL_PATH,
    VERIFICATION_THRESHOLD,
    PREPROCESSING_STEPS,
    EMBEDDING_SIZE,
    EMBEDDING_NORMALIZE
)
from .config.paths import (
    BASE_DIR,
    MODEL_DIR,
    DATA_DIR,
    ARCHIVE_DIR,
    MODEL_PATH,
    EMBEDDINGS_DIR,
    TEST_IMAGES_DIR
)

# Version information
__version__ = '1.0.0'

__all__ = [
    # Core
    'preprocess_image',
    'FaceEmbedding',
    'FaceVerifier',

    # Config
    'MODEL_INPUT_SIZE',
    'MODEL_PATH',
    'VERIFICATION_THRESHOLD',
    'PREPROCESSING_STEPS',
    'EMBEDDING_SIZE',
    'EMBEDDING_NORMALIZE',
    'BASE_DIR',
    'MODEL_DIR',
    'DATA_DIR',
    'ARCHIVE_DIR',
    'EMBEDDINGS_DIR',
    'TEST_IMAGES_DIR',

    # Version
    '__version__'
]
