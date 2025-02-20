import threading
from typing import Dict
from data.session import Session, SessionType
from typing import Optional


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}  # session_id: Session
        # Lock for thread safety (multiple threads can access the same session)
        self.lock = threading.Lock()

    def create_session(self, session_type: SessionType) -> Session:
        '''
        Create a new session and return it
        '''
        with self.lock:
            new_session = Session(session_type=session_type)
            self.sessions[new_session.session_id] = new_session
            return new_session

    # we use Optional to allow for the possibility of a session not being found
    # to be handled by the caller, rather than raising an exception
    def get_session(self, session_id: str) -> Optional[Session]:
        '''
        Get a session by its session_id
        '''
        with self.lock:
            return self.sessions.get(session_id)

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
            session.update_activity()

    def clean_expired_sessions(self, timeout: float):
        '''
        Clean up expired sessions

        Args:
            timeout (float): The session timeout in seconds

        Returns:
            int: The number of sessions cleaned up
        '''
        with self.lock:
            expired = [sid for sid, s in self.sessions.items()
                       if s.is_expired(timeout)]
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
