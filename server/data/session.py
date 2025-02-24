from dataclasses import dataclass, field
from typing import List, Optional
import time
import uuid
from enum import Enum


class SessionType(Enum):
    ACTIVATED = "activated"
    IMAGE_RECEIVED = "image_received"
    RFID_RECEIVED = "rfid_received"
    COMPLETE = "complete"
    # TODO: add in the emergency session type


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Store timestamps as Unix timestamps (float)
    created_at: float = field(default_factory=time.time)
    session_type: SessionType = SessionType.ACTIVATED

    # Authentication Data
    rfid_tag: Optional[str] = None
    embedding: Optional[List[float]] = None
    image_data: Optional[bytes] = None

    # System Metadata
    notification_sent: bool = False
    last_updated: float = field(default_factory=time.time)
    user_data: Optional[dict] = None
    verification_status: str = "pending"
    similarity_score: Optional[float] = None
    top_matches: Optional[List[dict]] = None

    def has_rfid(self) -> bool:
        return self.rfid_tag is not None

    def has_image(self) -> bool:
        return self.image_data is not None

    def is_expired(self, timeout: float) -> bool:
        """Check if session has expired"""
        return (time.time() - self.last_updated) > timeout

    def validate(self) -> bool:
        """Check required fields based on session type"""
        if self.session_type == SessionType.RFID_RECEIVED:
            return self.rfid_tag is not None
        if self.session_type == SessionType.IMAGE_RECEIVED:
            return self.image_data is not None
        return True

    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_updated = time.time()

    def update_verification_status(self, status: str, similarity: Optional[float] = None):
        """Update verification status and score"""
        self.verification_status = status
        self.similarity_score = similarity
        self.update_activity()

    def add_user_data(self, user_data: dict):
        """Add user data to session"""
        self.user_data = user_data
        self.update_activity()

    def add_top_matches(self, matches: List[dict]):
        """Add top matches for image-only verification"""
        self.top_matches = matches
        self.update_activity()
