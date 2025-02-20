from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


# Notification types and severity levels
class NotificationType(Enum):
    RFID_NOT_FOUND = "RFID Not Found"
    RFID_NOT_RECOGNIZED = "RFID Not Recognized"
    RFID_RECOGNIZED = "RFID Recognized"
    FACE_MISMATCH = "Face Mismatch"
    ACCESS_GRANTED = "Access Granted"
    FACE_NOT_RECOGNIZED = "Face Not Recognized"
    FACE_RECOGNIZED = "Face Recognized"
    MULTIPLE_FAILED_ATTEMPTS = "Multiple Failed Attempts"
    DEFAULT = "Default"


class SeverityLevel(Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"

@dataclass
class Notification:
    """
    A class to represent a notification in the Campus Security and Evacuation System.

    Attributes:
        id (str): Unique identifier for the notification.
        notification_type (NotificationType): Type of the notification.
        severity_level (SeverityLevel): Severity level of the notification.
        timestamp (datetime): Timestamp when the notification was created.
        location (Optional[str]): Location where the event occurred.
        rfid_id (Optional[str]): RFID identifier associated with the event.
        face_id (Optional[str]): Face identifier associated with the event.
        message (Optional[str]): Message describing the event.
        actions_required (Optional[str]): Actions required in response to the event.
        image_url (Optional[str]): URL of an image associated with the event.
        status (str): Status of the notification (e.g., 'Unread', 'Read').

    Methods:
        __str__(): Returns a string representation of the notification in markdown format.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # default; will be overwritten
    event_type: NotificationType = NotificationType.DEFAULT
    severity: SeverityLevel = SeverityLevel.INFO
    # TODO: fix the timestamp to be dd/mm/yyyy hh:mm:ss
    timestamp: str = field(
        default_factory=lambda: datetime.now().strftime("%d/%m/%Y %I:%M %p"))
    session_id: str = None
    user_id: str = None
    message: str = None
    image_url: str = None
    # stores the employee data and other data in the templates
    additional_data: dict = field(default_factory=dict)
    status: str = "Unread"

    def to_dict(self):
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
