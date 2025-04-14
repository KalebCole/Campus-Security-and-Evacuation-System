from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import uuid


class Session(BaseModel):
    """Session model for validating and processing session data from ESP32-CAM."""

    device_id: str = Field(..., description="ID of the ESP32-CAM device")
    session_id: str = Field(..., description="Unique session identifier")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    session_duration: int = Field(...,
                                  description="Duration of session in milliseconds")
    image_size: int = Field(..., description="Size of the image in bytes")
    image_data: str = Field(..., description="Base64 encoded image data")
    rfid_detected: bool = Field(..., description="Whether RFID was detected")
    face_detected: bool = Field(..., description="Whether a face was detected")
    free_heap: int = Field(..., description="Free heap memory in bytes")
    state: str = Field(..., description="Current state of the session")

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate that session_id is a valid UUID."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("session_id must be a valid UUID")

    @field_validator('image_size')
    @classmethod
    def validate_image_size(cls, v: int) -> int:
        """Validate that image size is within reasonable limits."""
        if v < 0:
            raise ValueError("image_size cannot be negative")
        if v > 10 * 1024 * 1024:  # 10MB max
            raise ValueError("image_size exceeds maximum allowed size")
        return v

    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate that state is one of the allowed values."""
        allowed_states = {'IDLE', 'CONNECTION',
                          'FACE_DETECTING', 'RFID_WAITING', 'SESSION'}
        if v not in allowed_states:
            raise ValueError(f"state must be one of {allowed_states}")
        return v

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "device_id": "esp32-cam-01",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": 1234567890,
                "session_duration": 5000,
                "image_size": 1024,
                "image_data": "base64_encoded_image",
                "rfid_detected": True,
                "face_detected": True,
                "free_heap": 20000,
                "state": "SESSION"
            }
        }
