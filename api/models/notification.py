from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
from typing import Optional, Dict, Any


class NotificationType(Enum):
    RFID_NOT_FOUND = "RFID Not Found"
    # RFID_NOT_DETECTED = "RFID Not Detected" # Merged into RFID_NOT_FOUND or handled implicitly?
    # Potentially useful for logging, maybe not alerting
    RFID_RECOGNIZED = "RFID Recognized"
    FACE_NOT_RECOGNIZED = "Face Not Recognized"
    ACCESS_GRANTED = "Access Granted"
    FACE_NOT_DETECTED = "Face Not Detected"  # If image has no face
    FACE_RECOGNIZED = "Face Recognized"  # Potentially useful for logging
    # Needs separate logic to track
    MULTIPLE_FAILED_ATTEMPTS = "Multiple Failed Attempts"
    SYSTEM_ERROR = "System Error"  # Added for internal errors
    DEFAULT = "Default"  # Should ideally not be used


class SeverityLevel(Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass
class Notification:
    """
    Represents a notification event within the system.

    Attributes:
        id (str): Unique identifier for the notification.
        event_type (NotificationType): Type of the notification event.
        severity (SeverityLevel): Severity level of the notification.
        timestamp (str): Timestamp when the notification was created (ISO format preferred).
        session_id (Optional[str]): Session ID associated with the event, if applicable.
        user_id (Optional[str]): User/Employee ID associated with the event, if known.
        message (Optional[str]): A descriptive message about the event.
        image_url (Optional[str]): URL of an associated image (if applicable, e.g., for manual review).
        additional_data (dict): Dictionary for any other relevant context.
        status (str): Status for tracking (e.g., 'Sent', 'Pending', 'Failed', 'Logged').
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: NotificationType = NotificationType.DEFAULT
    severity: SeverityLevel = SeverityLevel.INFO
    # Use UTC and ISO format
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None
    user_id: Optional[str] = None  # Can store employee ID here
    message: Optional[str] = None
    image_url: Optional[str] = None  # Consider how this will be populated/used
    additional_data: Dict[str, Any] = field(default_factory=dict)
    status: str = "Pending"  # Initial status

    def to_dict(self) -> Dict[str, Any]:
        """Convert the notification object to a dictionary."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "message": self.message,
            "image_url": self.image_url,
            "additional_data": self.additional_data,
            "status": self.status,
        }

    def __str__(self):
        """Provide a simple string representation."""
        return f"Notification(id={self.id}, type={self.event_type.name}, severity={self.severity.name}, session={self.session_id})"
