"""
Image preprocessing for face recognition using GhostFaceNets.
"""

import cv2
import numpy as np
from typing import Union, Tuple, Optional
import logging

logger = logging.getLogger(__name__)  # Add logger

# --- OpenCV DNN Face Detector Setup ---
# Correct paths assuming the script runs relative to the container's /app dir
# which maps to the face_recognition directory.
PROTOTXT_PATH = "core/models/detector/deploy.prototxt"
MODEL_PATH = "core/models/detector/res10_300x300_ssd_iter_140000.caffemodel"
CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence to consider a detection

# Load the network
try:
    face_detector_net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, MODEL_PATH)
    logger.info("Successfully loaded OpenCV DNN face detector model.")
except cv2.error as e:
    logger.error(
        f"Failed to load OpenCV DNN face detector model from {PROTOTXT_PATH} / {MODEL_PATH}: {e}", exc_info=True)
    logger.error(
        "Please ensure the model files are downloaded and paths are correct.")
    face_detector_net = None  # Indicate model loading failed
# ------------------------------------


def detect_face(image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """
    Detects the most prominent face using OpenCV DNN.

    Args:
        image: Input image (BGR format from OpenCV).

    Returns:
        Tuple containing bounding box (startX, startY, endX, endY) or None if no face found.
    """
    if face_detector_net is None:
        logger.error(
            "Face detector model not loaded. Cannot perform detection.")
        return None
    if not isinstance(image, np.ndarray) or image.size == 0:
        logger.warning("Invalid image provided to detect_face.")
        return None

    try:
        (h, w) = image.shape[:2]
        # Create blob (resized 300x300, mean subtraction values from training)
        blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                     (300, 300), (104.0, 177.0, 123.0))

        face_detector_net.setInput(blob)
        detections = face_detector_net.forward()

        best_detection_idx = -1
        highest_confidence = CONFIDENCE_THRESHOLD  # Start with threshold

        # Iterate over detections
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            # --- Add temporary debug log for ALL detection confidences ---
            logger.debug(
                f"  Potential detection {i} confidence: {confidence:.4f}")
            # -----------------------------------------------------------

            if confidence > highest_confidence:
                highest_confidence = confidence
                best_detection_idx = i

        if best_detection_idx != -1:
            # Compute bounding box coordinates
            box = detections[0, 0, best_detection_idx,
                             3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            # Ensure coordinates are within image bounds
            startX = max(0, startX)
            startY = max(0, startY)
            endX = min(w - 1, endX)
            endY = min(h - 1, endY)

            logger.debug(
                f"Face detected with confidence {highest_confidence:.2f} at box: ({startX}, {startY}, {endX}, {endY})")
            return (startX, startY, endX, endY)
        else:
            logger.warning(
                "No face detected meeting the confidence threshold.")
            return None

    except Exception as e:
        logger.error(f"Error during face detection: {e}", exc_info=True)
        return None


def align_face_simple(image: np.ndarray, bounding_box: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
    """
    Crops the face from the image based on the bounding box.
    (Simple alignment - no rotation/landmark alignment)

    Args:
        image: Original image.
        bounding_box: Tuple (startX, startY, endX, endY).

    Returns:
        Cropped face image as np.ndarray or None if cropping fails.
    """
    try:
        (startX, startY, endX, endY) = bounding_box
        # Basic validation
        if startX >= endX or startY >= endY:
            logger.warning(
                f"Invalid bounding box for cropping: {bounding_box}")
            return None

        # TODO: Consider adding margins here if needed, ensuring they stay within bounds

        cropped_face = image[startY:endY, startX:endX]

        if cropped_face.size == 0:
            logger.warning(
                f"Cropping resulted in empty image for box: {bounding_box}")
            return None

        logger.debug(
            f"Successfully cropped face to shape: {cropped_face.shape}")
        return cropped_face
    except Exception as e:
        logger.error(
            f"Error during simple face alignment (cropping): {e}", exc_info=True)
        return None

# --- Original Preprocessing (Now includes BGR->RGB) ---


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
    Preprocess a *cropped and aligned* face image for GhostFaceNets.
    NOW INCLUDES BGR->RGB CONVERSION.

    Args:
        image: Input **cropped/aligned** face image as numpy array (BGR or RGB).
        target_size: Target size for resizing (default: 112x112 for GhostFaceNets)
        normalize: Whether to normalize pixel values (default: True)

    Returns:
        Preprocessed image as numpy array (RGB, normalized)
    """
    if not isinstance(image, np.ndarray) or image.size == 0:
        logger.warning("Invalid image passed to preprocess_image.")
        return None

    try:
        # Convert BGR to RGB (Models typically trained on RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        logger.debug("Converted image BGR -> RGB")

        # Resize image
        resized = cv2.resize(rgb_image, target_size)
        logger.debug(f"Resized image to {target_size}")

        # Convert to float32 and normalize for GhostFaceNets
        # GhostFaceNets expects pixel values in range [-1, 1]
        if normalize:
            resized = resized.astype(np.float32)
            resized = (resized - 127.5) / 128.0
            logger.debug("Normalized pixel values to [-1, 1]")

        return resized
    except Exception as e:
        logger.error(
            f"Error during final preprocessing (resize/normalize): {e}", exc_info=True)
        return None


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
