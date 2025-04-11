"""
Path configurations for the face recognition module.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "core" / "models"
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = BASE_DIR / "archive"

# Model file paths
MODEL_PATH = MODEL_DIR / "ghostfacenets.h5"

# Data directories
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
TEST_IMAGES_DIR = BASE_DIR / "tests" / "test_images"

# Create directories if they don't exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(TEST_IMAGES_DIR, exist_ok=True)
