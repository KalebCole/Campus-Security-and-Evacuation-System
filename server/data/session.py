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
    session_id: str = field(default_factory=lambda: str(
        uuid.uuid4()))  # unique identifier for the session
    # timestamp of session creation
    created_at: float = field(default_factory=time.time)
    session_type: SessionType = SessionType.ACTIVATED  # type of session

    # Authentication Data (we use optional to allow for partial sessions)
    rfid_tag: Optional[str] = None
    # adds the embedding to the session after the image is received and processed
    embedding: Optional[List[float]] = None
    # following the embedding being added to the session, this session can be considered complete
    image_data: Optional[bytes] = None

    # System Metadata
    notification_sent: bool = False
    # TODO: these are stretch fields. We can add them in the future
    last_updated: float = field(default_factory=time.time)  # Add this field
    user_data: Optional[dict] = None  # Add user data field
    verification_status: str = "pending"

    # used for notifications and logging and for the web app to display the top matches
    similarity_score: Optional[float] = None
    top_matches: Optional[List[dict]] = None

    def has_rfid(self) -> bool:
        return self.rfid_tag is not None

    def has_image(self) -> bool:
        return self.image_data is not None

    def is_expired(self, timeout: float) -> bool:
        return (time.time() - self.created_at) > timeout

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
