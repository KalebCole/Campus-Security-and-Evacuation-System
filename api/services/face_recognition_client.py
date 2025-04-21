"""Client for communicating with the Face Recognition service."""

import requests
import logging
import numpy as np  # Added for cosine similarity
from typing import Optional, List, Dict, Any

from config import Config  # Import Config to access environment variables

logger = logging.getLogger(__name__)


class FaceRecognitionClientError(Exception):
    """Custom exception for Face Recognition client errors."""
    pass


class FaceRecognitionClient:
    """Handles HTTP communication with the face recognition service (DeepFace)."""

    def __init__(self):
        """Initialize the client with the service URL from config."""
        self.service_url = Config.FACE_RECOGNITION_URL
        if not self.service_url:
            raise FaceRecognitionClientError(
                "FACE_RECOGNITION_URL is not configured.")
        logger.info(
            f"Face Recognition Client initialized for URL: {self.service_url}")
        # Store threshold for local verification
        self.verification_threshold = Config.FACE_VERIFICATION_THRESHOLD
        logger.info(
            f"Using verification threshold: {self.verification_threshold}")

    def get_embedding(self, image_base64: str) -> Optional[List[float]]:
        """
        Requests an embedding for the given base64 encoded image string
        using the DeepFace /represent endpoint.

        Args:
            image_base64: The base64 encoded string of the image
                          (expected to include data URI prefix e.g., data:image/jpeg;base64,...).

        Returns:
            A list of floats representing the embedding, or None if an error occurs.
        """
        logger.info(f"Getting embedding for image: {image_base64}")
        # /represent for DeepFace
        endpoint = f"{self.service_url}/represent"
        
        # Updated payload structure for DeepFace /represent
        payload = {
            "img_path": image_base64,
            "model_name": "GhostFaceNet",  # Specify model
            "detector_backend": "opencv"  # Specify detector (can be tuned)
        }
        logger.debug(f"Requesting embedding from DeepFace {endpoint}")

        try:
            response = requests.post(
                endpoint, json=payload, timeout=15)  # Increased timeout slightly
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            # Updated response parsing based on typical DeepFace /represent structure
            results = data.get("results")
            if isinstance(results, list) and len(results) > 0:
                embedding = results[0].get("embedding")
                if isinstance(embedding, list):
                    logger.debug(
                        f"Successfully received embedding of dimension {len(embedding)} via DeepFace")
                    return embedding
                else:
                    logger.error(
                        f"'embedding' key missing or not a list in DeepFace result: {results[0]}")
                    raise FaceRecognitionClientError(
                        "Invalid embedding format in DeepFace response.")
            else:
                logger.error(
                    f"'results' key missing or not a list in DeepFace response: {data}")
                raise FaceRecognitionClientError(
                    "Invalid results format in DeepFace response.")

        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout connecting to DeepFace service at {endpoint}")
            raise FaceRecognitionClientError(
                "Timeout connecting to DeepFace service.")
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Connection error when connecting to DeepFace service at {endpoint}")
            raise FaceRecognitionClientError(
                "Could not connect to DeepFace service.")
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error from DeepFace service ({endpoint}): {e.response.status_code} - {e.response.text}")
            raise FaceRecognitionClientError(
                f"DeepFace service returned error: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error during request to DeepFace service ({endpoint}): {str(e)}")
            raise FaceRecognitionClientError(f"Request failed: {str(e)}")
        # Handle potential JSON parsing/indexing errors
        except (KeyError, ValueError, IndexError) as e:
            logger.error(
                f"Error parsing response from DeepFace service ({endpoint}): {str(e)}")
            raise FaceRecognitionClientError(
                f"Invalid response format from DeepFace service: {str(e)}")

    # --- Verification Now Done Locally ---
    def verify_embeddings(self, embedding1: List[float], embedding2: List[float]) -> Optional[Dict[str, Any]]:
        """
        Verifies if two embeddings match using cosine similarity and configured threshold.
        This is now performed locally, not by calling the DeepFace service.

        Args:
            embedding1: The first embedding (list of floats).
            embedding2: The second embedding (list of floats).

        Returns:
            A dictionary containing 'is_match' (bool) and 'confidence' (float),
            or None if input is invalid.
        """
        logger.debug("Performing local embedding verification...")
        if not embedding1 or not embedding2:
            logger.warning(
                "Verification failed: One or both embeddings are missing.")
            return None

        try:
            # Ensure embeddings are numpy arrays
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)

            if emb1.shape != emb2.shape:
                logger.warning(
                    f"Verification failed: Embeddings have different shapes: {emb1.shape} vs {emb2.shape}")
                return None

            # Calculate cosine similarity (dot product of normalized vectors)
            # Assuming embeddings from DeepFace/GhostFaceNet are already normalized
            similarity = np.dot(emb1, emb2)

            # Clamp similarity score between 0 and 1 (cosine similarity can be slightly > 1 due to precision)
            similarity = float(np.clip(similarity, 0.0, 1.0))

            # Determine if it's a match based on the threshold from config
            is_match = similarity >= self.verification_threshold

            logger.debug(
                f"Verification result: Similarity={similarity:.4f}, Threshold={self.verification_threshold}, Match={is_match}")
            return {"is_match": is_match, "confidence": similarity}

        except Exception as e:
            logger.error(
                f"Error during local embedding verification: {e}", exc_info=True)
            # Return None or raise an error depending on desired handling
            # Returning None indicates verification couldn't be performed
            return None

    def check_health(self) -> bool:
        """Check if DeepFace service is responding at its root."""
        # DeepFace often responds at the root URL
        endpoint = f"{self.service_url}/"  # Changed endpoint
        logger.debug(f"Checking health of DeepFace service at {endpoint}")
        try:
            # Shorter timeout for health check
            response = requests.get(endpoint, timeout=5)
            # Check for 200 OK or potentially other success/redirect codes if needed
            is_healthy = 200 <= response.status_code < 300
            logger.debug(
                f"DeepFace health check status code: {response.status_code}, Healthy: {is_healthy}")
            return is_healthy
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Health check failed for DeepFace service at {endpoint}: {str(e)}")
            return False
