"""
Configuration settings for the face recognition system.
"""

# Model settings
MODEL_INPUT_SIZE = (112, 112)
MODEL_PATH = "face_recognition/core/models/ghostfacenets.h5"

# Verification settings
VERIFICATION_THRESHOLD = 0.6

# Preprocessing settings
PREPROCESSING_STEPS = [
    "resize",
    "normalize",
    "align"
]

# Embedding settings
EMBEDDING_SIZE = 512
EMBEDDING_NORMALIZE = True
