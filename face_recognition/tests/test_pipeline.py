"""
Test suite for the face recognition pipeline using GhostFaceNets.
"""

import os
import cv2
import numpy as np
import pytest
from ..core.preprocessing import preprocess_image
from ..core.embedding import FaceEmbedding
from ..core.verification import FaceVerifier
from ..config.paths import TEST_IMAGES_DIR, MODEL_PATH

# Helper functions for testing


def validate_image(image):
    """Check if an image is valid for processing."""
    if image is None:
        return False
    if not isinstance(image, np.ndarray):
        return False
    if image.size == 0:
        return False
    if len(image.shape) < 2:
        return False
    return True


def check_image_quality(image):
    """Check basic image quality."""
    if not validate_image(image):
        return False

    # Convert to grayscale if color
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Check brightness
    mean_brightness = np.mean(gray)
    if mean_brightness < 20 or mean_brightness > 240:
        return False

    # Check contrast
    std_dev = np.std(gray)
    if std_dev < 20:  # Low contrast
        return False

    return True


class TestFaceRecognitionPipeline:
    @pytest.fixture
    def face_embedding(self):
        return FaceEmbedding(model_path=str(MODEL_PATH))

    @pytest.fixture
    def face_verifier(self):
        return FaceVerifier()

    def test_complete_pipeline(self, face_embedding, face_verifier):
        """Test the complete face recognition pipeline."""
        # Load test images
        person1_img1 = cv2.imread(os.path.join(
            TEST_IMAGES_DIR, 'person1_1.jpg'))
        person1_img2 = cv2.imread(os.path.join(
            TEST_IMAGES_DIR, 'person1_2.jpg'))
        person2_img1 = cv2.imread(os.path.join(
            TEST_IMAGES_DIR, 'person2_1.jpg'))

        # Preprocess images
        processed1 = preprocess_image(person1_img1)
        processed2 = preprocess_image(person1_img2)
        processed3 = preprocess_image(person2_img1)

        # Generate embeddings
        embedding1 = face_embedding.generate_embedding(processed1)
        embedding2 = face_embedding.generate_embedding(processed2)
        embedding3 = face_embedding.generate_embedding(processed3)

        # Verify matches
        is_match1, similarity1 = face_verifier.verify_faces(
            embedding1, embedding2)
        is_match2, similarity2 = face_verifier.verify_faces(
            embedding1, embedding3)

        # Assert results
        assert is_match1  # Same person
        assert not is_match2  # Different people

    def test_error_handling(self, face_embedding):
        """Test error handling in the pipeline."""
        # Test invalid image
        invalid_image = np.zeros((100, 100))  # 2D array
        assert not validate_image(invalid_image)

        # Test empty image
        empty_image = np.array([])
        assert not validate_image(empty_image)

        # Test None input
        assert not validate_image(None)

    def test_image_quality(self):
        """Test image quality checks."""
        # Load test images
        valid_image = cv2.imread(os.path.join(TEST_IMAGES_DIR, 'valid.jpg'))
        grayscale_image = cv2.imread(
            os.path.join(TEST_IMAGES_DIR, 'grayscale.jpg'))

        # Test good quality image
        assert check_image_quality(valid_image)

        # Test grayscale image
        assert check_image_quality(grayscale_image)

        # Test low contrast image
        low_contrast = np.full((100, 100, 3), 128, dtype=np.uint8)
        assert not check_image_quality(low_contrast)

        # Test too dark image
        dark_image = np.full((100, 100, 3), 5, dtype=np.uint8)
        assert not check_image_quality(dark_image)

        # Test too bright image
        bright_image = np.full((100, 100, 3), 250, dtype=np.uint8)
        assert not check_image_quality(bright_image)
