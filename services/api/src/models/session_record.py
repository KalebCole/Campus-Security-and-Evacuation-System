import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID

from .database import Base  # Import Base from models/database.py


class SessionRecord(Base):
    """Database model for session tracking."""
    __tablename__ = 'session_records'

    # Assuming you might want a dedicated table for sessions
    # If not, this model might not be needed if session data is only in AccessLog/VerificationImage
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String, nullable=False)
    state = Column(String, nullable=False)
    # Consider timezone=True if needed
    start_time = Column(DateTime, nullable=False)
    # Consider timezone=True if needed
    last_update = Column(DateTime, nullable=False)
    face_detected = Column(Boolean, default=False)
    rfid_detected = Column(Boolean, default=False)
    is_expired = Column(Boolean, default=False)

    def __repr__(self):
        return f"<SessionRecord(id={self.id}, device_id='{self.device_id}', state='{self.state}')>"
