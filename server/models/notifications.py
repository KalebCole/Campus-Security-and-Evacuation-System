from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid


class NotificationType(Enum):
    RFID_ACCESS_GRANTED = 'RFID Access Granted'
    RFID_ACCESS_DENIED = 'RFID Access Denied'
    FACE_RECOGNIZED = 'Face Recognized'
    FACE_NOT_RECOGNIZED = 'Face Not Recognized'
    SYSTEM_ALERT = 'System Alert'
    # TODO: do i need to make more types of notifications? like for rfid but not face, etc.


class SeverityLevel(Enum):
    INFO = 'Info'
    WARNING = 'Warning'
    CRITICAL = 'Critical'


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
    notification_type: NotificationType = NotificationType.SYSTEM_ALERT
    severity_level: SeverityLevel = SeverityLevel.INFO
    timestamp: datetime = field(default_factory=datetime.utcnow)
    location: Optional[str] = None
    rfid_id: Optional[str] = None
    face_id: Optional[str] = None
    message: Optional[str] = None
    actions_required: Optional[str] = None
    image_url: Optional[str] = None
    status: str = 'Unread'

    def __str__(self):
        current_timestamp = self.timestamp.isoformat()
        markdown_message = f"""
        **{current_timestamp} - {self.notification_type.value}**
        **Severity:** {self.severity_level.value}
        **Location:** {self.location or 'N/A'}
        **RFID ID:** {self.rfid_id or 'N/A'}
        **Face ID:** {self.face_id or 'N/A'}
        **Message:** {self.message or 'N/A'}
        **Actions Required:** {self.actions_required or 'N/A'}
        **Status:** {self.status}
        """
        if self.image_url:
            markdown_message += f"\n![Image]({self.image_url})"

        return markdown_message.strip()
