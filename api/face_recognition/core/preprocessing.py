"""
Image preprocessing for face recognition using GhostFaceNets.
"""

import cv2
import numpy as np
from typing import Union, Tuple, Optional


def validate_image(image: np.ndarray) -> bool:
    """
    Validate the input image meets basic requirements.

    Args:
        image: Input image to validate

    Returns:
        bool: True if image is valid, False otherwise
    """
    if image is None:
        return False
    if not isinstance(image, np.ndarray):
        return False
    if image.size == 0:
        return False
    if len(image.shape) != 3:  # Must be 3D array (H, W, C)
        return False
    if image.shape[2] != 3:  # Must have 3 channels (RGB)
        return False
    return True


def preprocess_image(
    image: np.ndarray,
    target_size: Tuple[int, int] = (112, 112),
    normalize: bool = True
) -> np.ndarray:
    """
    Preprocess an image for GhostFaceNets face recognition.

    Args:
        image: Input image as numpy array
        target_size: Target size for resizing (default: 112x112 for GhostFaceNets)
        normalize: Whether to normalize pixel values (default: True)

    Returns:
        Preprocessed image as numpy array
    """
    # Resize image
    resized = cv2.resize(image, target_size)

    # Convert to float32 and normalize for GhostFaceNets
    # GhostFaceNets expects pixel values in range [-1, 1]
    if normalize:
        resized = resized.astype(np.float32)
        resized = (resized - 127.5) / 128.0

    return resized


def check_image_quality(image: np.ndarray) -> bool:
    """
    Perform basic quality checks on the image.

    Args:
        image: Input image to check

    Returns:
        bool: True if image passes quality checks
    """
    try:
        # Check for completely black or white images
        if np.mean(image) < 10 or np.mean(image) > 245:
            return False

        # Check for sufficient contrast
        if np.std(image) < 20:
            return False

        return True
    except:
        return False
