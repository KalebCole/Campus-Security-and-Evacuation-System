# add the root path to the sys.path
from app_config import Config
import uuid
import time
from dataclasses import dataclass
import sys
import os

server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, server_dir)


class SessionType:
    RFID_RECEIVED = "rfid_received"
    IMAGE_RECEIVED = "image_received"
    VERIFICATION_COMPLETE = "verification_complete"


@dataclass
class Session:
    def __init__(self, session_id=None, session_type=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.session_type = session_type
        self.created_at = time.time()
        self.last_updated = time.time()
        self.rfid_tag = None  # RFID tag entry from the Mega
        self.image_data = None  # Image entry from the ESP32
        self.embedding = None  # Face embedding generated from the image sent by the ESP32
        self.user_data = None  # User entry from the database
        # Verification result from the process_verification function
        self.verification_result = None

    def is_complete(self):
        return self.rfid_tag and self.embedding

    def is_expired(self):
        # Check if the session has expired based on the last_updated time and the timeout
        return time.time() - self.last_updated > Config.SESSION_TIMEOUT

    def update(self, **kwargs):
        self.last_updated = time.time()
        for key, value in kwargs.items():
            # setattr is a built-in function that sets the value of the attribute of an object.
            setattr(self, key, value)
