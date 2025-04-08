"""
Test suite for image preprocessing functionality.
"""

import unittest
import numpy as np
import cv2
from pathlib import Path
from typing import Optional
from ..core.preprocessing import (
    preprocess_image
)
from ..config.paths import TEST_IMAGES_DIR

# Import helper functions from test_pipeline.py
from .test_pipeline import validate_image, check_image_quality


class TestPreprocessing(unittest.TestCase):
    def setUp(self):
        """Set up test cases with sample images."""
        # Create test directory if it doesn't exist
        self.test_dir = Path(TEST_IMAGES_DIR)
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Load sample test images from test_images directory
        self.valid_image = cv2.imread(str(self.test_dir / "valid.jpg"))
        self.grayscale_image = cv2.imread(str(self.test_dir / "grayscale.jpg"))
        self.rgba_image = cv2.imread(
            str(self.test_dir / "rgba.png"), cv2.IMREAD_UNCHANGED)
        self.small_image = cv2.imread(str(self.test_dir / "small.jpg"))
        self.large_image = cv2.imread(str(self.test_dir / "large.jpg"))

    def test_validate_image(self):
        """Test image validation function."""
        # Test valid image
        self.assertTrue(validate_image(self.valid_image))

        # Test invalid cases
        self.assertFalse(validate_image(None))
        self.assertFalse(validate_image(np.array([])))
        self.assertFalse(validate_image(np.array([1, 2, 3])))  # 1D array
        self.assertFalse(validate_image(
            np.array([[1, 2], [3, 4]])))  # 2D array

    def test_preprocess_image(self):
        """Test image preprocessing function."""
        # Test valid RGB image
        processed = preprocess_image(self.valid_image)
        self.assertIsNotNone(processed)
        self.assertEqual(processed.shape, (1, 112, 112, 3))
        self.assertTrue(np.all(processed >= -1) and np.all(processed <= 1))

        # Test grayscale conversion
        processed = preprocess_image(self.grayscale_image)
        self.assertIsNotNone(processed)
        self.assertEqual(processed.shape, (1, 112, 112, 3))

        # Test RGBA conversion
        processed = preprocess_image(self.rgba_image)
        self.assertIsNotNone(processed)
        self.assertEqual(processed.shape, (1, 112, 112, 3))

        # Test resizing
        processed = preprocess_image(self.small_image)
        self.assertIsNotNone(processed)
        self.assertEqual(processed.shape, (1, 112, 112, 3))

        processed = preprocess_image(self.large_image)
        self.assertIsNotNone(processed)
        self.assertEqual(processed.shape, (1, 112, 112, 3))

    def test_check_image_quality(self):
        """Test image quality check function."""
        # Test good quality image
        self.assertTrue(check_image_quality(self.valid_image))

        # Test black image
        black_image = np.zeros((112, 112, 3), dtype=np.uint8)
        self.assertFalse(check_image_quality(black_image))

        # Test white image
        white_image = np.ones((112, 112, 3), dtype=np.uint8) * 255
        self.assertFalse(check_image_quality(white_image))

        # Test low contrast image
        low_contrast = np.ones((112, 112, 3), dtype=np.uint8) * 128
        self.assertFalse(check_image_quality(low_contrast))

    def test_error_handling(self):
        """Test error handling in preprocessing."""
        # Test with invalid input
        self.assertIsNone(preprocess_image(None))
        self.assertIsNone(preprocess_image(np.array([])))

        # Test with corrupted image data
        corrupted = np.random.randint(0, 255, (112, 112, 5), dtype=np.uint8)
        self.assertIsNone(preprocess_image(corrupted))

    def test_performance(self):
        """Test preprocessing performance."""
        import time

        # Test processing time for different image sizes
        sizes = [(50, 50), (112, 112), (300, 300), (500, 500)]
        for size in sizes:
            image = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
            start_time = time.time()
            processed = preprocess_image(image)
            end_time = time.time()

            self.assertIsNotNone(processed)
            processing_time = end_time - start_time
            print(f"Processing time for {size}: {processing_time:.4f} seconds")

            # Ensure processing time is reasonable (less than 1 second)
            self.assertLess(processing_time, 1.0)


if __name__ == '__main__':
    unittest.main()
