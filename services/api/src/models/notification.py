from datetime import datetime
from enum import Enum
import uuid
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func  # For server-side default timestamp
from .database import Base  # Assuming your SQLAlchemy Base is in models/database.py
from pydantic import BaseModel, Field


class NotificationType(Enum):
    RFID_NOT_FOUND = "RFID Not Found"
    RFID_RECOGNIZED = "RFID Recognized"
    FACE_NOT_RECOGNIZED = "Face Not Recognized"
    ACCESS_GRANTED = "Access Granted"
    FACE_NOT_DETECTED = "Face Not Detected"
    FACE_RECOGNIZED = "Face Recognized"
    MULTIPLE_FAILED_ATTEMPTS = "Multiple Failed Attempts"
    SYSTEM_ERROR = "System Error"
    MANUAL_REVIEW_REQUIRED = "Manual Review Required"
    EMERGENCY_OVERRIDE = "Emergency Override Triggered"
    DEFAULT = "Default"


class SeverityLevel(Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITICAL = "Critical"


class Notification(BaseModel):
    """
    Represents a notification event within the system (Pydantic Model).

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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: NotificationType = NotificationType.DEFAULT
    severity: SeverityLevel = SeverityLevel.INFO
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    message: Optional[str] = None
    image_url: Optional[str] = None
    additional_data: Dict[str, Any] = Field(default_factory=dict)
    status: str = "Pending"

    def __str__(self):
        """Provide a simple string representation."""
        return f"Notification(id={self.id}, type={self.event_type.name}, severity={self.severity.name}, session={self.session_id})"

    class Config:
        # Pydantic v2 uses model_config dictionary
        model_config = {
            "use_enum_values": True,
            "arbitrary_types_allowed": True
        }


# --- SQLAlchemy Model for Database History ---


class NotificationHistory(Base):
    __tablename__ = 'notification_history'

    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default=func.gen_random_uuid())
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True),
                       nullable=False, server_default=func.now())
    session_id = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        'employees.id', ondelete='SET NULL'), nullable=True)
    message = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    additional_data = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NotificationHistory(id={self.id}, event_type='{self.event_type}', timestamp='{self.timestamp}')>"
