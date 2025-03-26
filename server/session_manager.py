import threading
from typing import Dict, Optional
import time
import uuid
from data.session import Session, SessionType


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}  # session_id: Session
        # Lock for thread safety (multiple threads can access the same session)
        self.lock = threading.Lock()

    def create_session(self, session_type: SessionType) -> Session:
        '''
        Create a new session and adds it to the session dictionary and returns it
        '''
        with self.lock:
            new_session = Session(session_type=session_type)
            self.sessions[new_session.session_id] = new_session
            return new_session

    def create_session_id(self) -> str:
        '''
        Creates a unique session_id for a new session
        '''
        return str(uuid.uuid4())

    # we use Optional to allow for the possibility of a session not being found
    # to be handled by the caller, rather than raising an exception
    def get_session(self, session_id: str) -> Optional[Session]:
        '''
        Get a session by its session_id from the dictionary
        '''
        with self.lock:
            return self.sessions.get(session_id)

    def get_session_id(self) -> Optional[str]:
        '''
        Simply returns the first session ID in the dictionary if any exists.
        Assumes at most one session exists at a time.

        Returns:
            Optional[str]: An existing session ID if found, otherwise None
        '''
        with self.lock:
            # If there are no sessions, return None
            if not self.sessions:
                return None

            # Since we assume there's at most one session, we can just get any key
            # This is the most efficient way to get a single key from a dictionary
            return next(iter(self.sessions))

    def update_session(self, session_id: str, **kwargs):
        '''
        Update a session with new values

        Args:
            session_id (str): The session_id of the session to update
            **kwargs: The fields to update and their new values

        Raises:
            KeyError: If the session_id is not found
            AttributeError: If an invalid field is provided

        Usage:
            update_session("session_id", embedding=[1, 2, 3], image_data=b"image")        
        '''
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise KeyError(f"Session {session_id} not found")

            for key, value in kwargs.items():
                if not hasattr(session, key):
                    raise AttributeError(
                        f"Invalid field {key} for Session")
                setattr(session, key, value)
            session.last_updated = time.time()

    def clean_expired_sessions(self):
        '''
        Clean up expired sessions

        Args:
            timeout (float): The session timeout in seconds

        Returns:
            int: The number of sessions cleaned up
        '''
        with self.lock:  # lock the session manager to prevent other threads from accessing it
            # List comprehension to get all expired sessions
            expired = [sid for sid, s in self.sessions.items()
                       if s.is_expired()]
            # Remove all expired sessions
            for sid in expired:
                del self.sessions[sid]
            return len(expired)

    def remove_session(self, session_id: str) -> bool:
        """
        Remove a session by its ID.

        Args:
            session_id (str): The ID of the session to remove

        Returns:
            bool: True if session was removed, False if session wasn't found
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    def get_all_sessions(self) -> Dict[str, Session]:
        """
        Get all active sessions.

        Returns:
            Dict[str, Session]: Dictionary of all active sessions, keyed by session_id
        """
        with self.lock:
            return self.sessions.copy()  # Return a copy to prevent external modification
