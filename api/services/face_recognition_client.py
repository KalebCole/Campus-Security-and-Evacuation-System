"""Client for communicating with the Face Recognition service."""

import requests
import logging
from typing import Optional, List, Dict, Any

from config import Config  # Import Config to access environment variables

logger = logging.getLogger(__name__)


class FaceRecognitionClientError(Exception):
    """Custom exception for Face Recognition client errors."""
    pass


class FaceRecognitionClient:
    """Handles HTTP communication with the face recognition service."""

    def __init__(self):
        """Initialize the client with the service URL from config."""
        self.service_url = Config.FACE_RECOGNITION_URL
        if not self.service_url:
            raise FaceRecognitionClientError(
                "FACE_RECOGNITION_URL is not configured.")
        logger.info(
            f"Face Recognition Client initialized for URL: {self.service_url}")

    def get_embedding(self, image_base64: str) -> Optional[List[float]]:
        """
        Requests an embedding for the given base64 encoded image string.

        Args:
            image_base64: The base64 encoded string of the image.

        Returns:
            A list of floats representing the embedding, or None if an error occurs.
        """
        endpoint = f"{self.service_url}/embed"  # Corrected endpoint
        payload = {"image": image_base64}  # Corrected payload key
        logger.debug(f"Requesting embedding from {endpoint}")

        try:
            response = requests.post(
                endpoint, json=payload, timeout=10)  # Added timeout
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            embedding = data.get("embedding")

            if isinstance(embedding, list):
                logger.debug(
                    f"Successfully received embedding of dimension {len(embedding)}")
                return embedding
            else:
                logger.error(
                    f"Invalid embedding format received from {endpoint}: {embedding}")
                raise FaceRecognitionClientError(
                    "Invalid embedding format received.")

        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout connecting to face recognition service at {endpoint}")
            raise FaceRecognitionClientError(
                "Timeout connecting to face service.")
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Connection error when connecting to face recognition service at {endpoint}")
            raise FaceRecognitionClientError(
                "Could not connect to face service.")
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error from face recognition service ({endpoint}): {e.response.status_code} - {e.response.text}")
            raise FaceRecognitionClientError(
                f"Face service returned error: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error during request to face recognition service ({endpoint}): {str(e)}")
            raise FaceRecognitionClientError(f"Request failed: {str(e)}")
        except (KeyError, ValueError) as e:  # Handle potential JSON parsing or missing key errors
            logger.error(
                f"Error parsing response from face recognition service ({endpoint}): {str(e)}")
            raise FaceRecognitionClientError(
                f"Invalid response format from face service: {str(e)}")

    def verify_embeddings(self, embedding1: List[float], embedding2: List[float]) -> Optional[Dict[str, Any]]:
        """
        Requests verification if two embeddings match.

        Args:
            embedding1: The first embedding (list of floats).
            embedding2: The second embedding (list of floats).

        Returns:
            A dictionary containing 'is_match' (bool) and 'confidence' (float),
            or None if an error occurs.
        """
        endpoint = f"{self.service_url}/verify"  # Corrected endpoint
        payload = {
            "embedding1": embedding1,
            "embedding2": embedding2
        }
        logger.debug(f"Requesting verification from {endpoint}")

        try:
            response = requests.post(
                endpoint, json=payload, timeout=10)  # Added timeout
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            is_match = data.get("is_match")
            confidence = data.get("confidence")

            if isinstance(is_match, bool) and isinstance(confidence, (float, int)):
                logger.debug(
                    f"Successfully received verification result: match={is_match}, confidence={confidence:.4f}")
                return {"is_match": is_match, "confidence": float(confidence)}
            else:
                logger.error(
                    f"Invalid verification format received from {endpoint}: {data}")
                raise FaceRecognitionClientError(
                    "Invalid verification format received.")

        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout connecting to face recognition service at {endpoint}")
            raise FaceRecognitionClientError(
                "Timeout connecting to face service.")
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Connection error when connecting to face recognition service at {endpoint}")
            raise FaceRecognitionClientError(
                "Could not connect to face service.")
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error from face recognition service ({endpoint}): {e.response.status_code} - {e.response.text}")
            raise FaceRecognitionClientError(
                f"Face service returned error: {e.response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error during request to face recognition service ({endpoint}): {str(e)}")
            raise FaceRecognitionClientError(f"Request failed: {str(e)}")
        except (KeyError, ValueError) as e:  # Handle potential JSON parsing or missing key errors
            logger.error(
                f"Error parsing response from face recognition service ({endpoint}): {str(e)}")
            raise FaceRecognitionClientError(
                f"Invalid response format from face service: {str(e)}")

    def check_health(self) -> bool:
        """Check if face recognition service is healthy."""
        endpoint = f"{self.service_url}/health"  # Endpoint was already correct
        try:
            # Shorter timeout for health check
            response = requests.get(endpoint, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Health check failed for face recognition service at {endpoint}: {str(e)}")
            return False
