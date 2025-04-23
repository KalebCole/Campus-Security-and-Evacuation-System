from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import uuid
import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)



class Session(BaseModel):
    """Session model for validating and processing session data from ESP32-CAM."""

    device_id: str = Field(..., description="ID of the ESP32-CAM device")
    session_id: str = Field(..., description="Unique session identifier")
    timestamp: datetime = Field(...,
                                description="Timestamp in ISO 8601 format")
    session_duration: int = Field(...,
                                  description="Duration of session in milliseconds")
    image_size: int = Field(..., description="Size of the image in bytes")
    image: Optional[str] = Field(
        None, description="Base64 encoded image data (optional)")
    rfid_detected: bool = Field(..., description="Whether RFID was detected")
    rfid_tag: Optional[str] = Field(
        None, description="The actual RFID tag value if detected (optional)")
    face_detected: bool = Field(..., description="Whether a face was detected")


    @field_validator('image_size')
    @classmethod
    def validate_image_size(cls, v: int) -> int:
        """Validate that image size is within reasonable limits."""
        if v < 0:
            raise ValueError("image_size cannot be negative")
        if v > 10 * 1024 * 1024:  # 10MB max
            raise ValueError("image_size exceeds maximum allowed size")
        return v


    @field_validator('image', mode='before')
    @classmethod
    def check_image_data(cls, v, values):
        """Ensure image_data is present if face_detected is true."""
        # This validator is tricky because face_detected might not be available yet
        # A root validator might be better if strict validation is needed
        # For now, we make image_data optional and handle its absence in the MQTT handler
        return v

    @field_validator('rfid_tag', mode='before')
    @classmethod
    def check_rfid_tag(cls, v, values):
        """Ensure rfid_tag is present if rfid_detected is true."""
        # Similar to image_data, strict validation here is complex.
        # The MQTT handler checks for rfid_tag if rfid_detected is true.
        return v

    # @field_validator('image', mode='before')
    # @classmethod
    # def extract_base64_from_data_uri(cls, v):
    #     """Extract base64 from data URI."""
    #     # Use regex to match data URI
    #     match = re.search(r'data:image/(png|jpeg);base64,(.*)', v)
    #     logger.debug(f"Extracted base64 from data URI: {match}")
    #     if match:
    #         # Return only the data part if it matches the pattern
    #         return match.group('data')
    #     # Return original value if no match
    #     return v

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "device_id": "esp32-cam-01",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2025-04-15T12:00:00Z",
                "session_duration": 5000,
                "image_size": 1024,
                "image": "base64_encoded_image",
                "rfid_detected": True,
                "rfid_tag": "A1B2C3D4",
                "face_detected": True,
            }
        }
