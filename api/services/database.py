from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import create_engine, Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from config import Config
import uuid

Base = declarative_base()


class SessionRecord(Base):
    """Database model for session tracking."""
    __tablename__ = 'session_records'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String, nullable=False)
    state = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    last_update = Column(DateTime, nullable=False)
    face_detected = Column(Boolean, default=False)
    rfid_detected = Column(Boolean, default=False)
    is_expired = Column(Boolean, default=False)


class DatabaseService:
    """Service for handling database operations."""

    def __init__(self, connection_string: str):
        """Initialize database service."""
        try:
            self.engine = create_engine(connection_string)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to initialize database: {str(e)}")

    def create_session(self, device_id: str, state: str) -> SessionRecord:
        """Create a new session record."""
        try:
            session = self.Session()
            now = datetime.utcnow()
            record = SessionRecord(
                device_id=device_id,
                state=state,
                start_time=now,
                last_update=now
            )
            session.add(record)
            session.commit()
            return record
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Failed to create session: {str(e)}")

    def update_session(self, session_id: uuid.UUID, state: str,
                       face_detected: bool = None, rfid_detected: bool = None) -> Optional[SessionRecord]:
        """Update an existing session record."""
        try:
            session = self.Session()
            record = session.query(SessionRecord).filter(
                SessionRecord.id == session_id).first()
            if record:
                record.state = state
                record.last_update = datetime.utcnow()
                if face_detected is not None:
                    record.face_detected = face_detected
                if rfid_detected is not None:
                    record.rfid_detected = rfid_detected
                session.commit()
            return record
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Failed to update session: {str(e)}")

    def get_active_sessions(self) -> List[SessionRecord]:
        """Get all active (non-expired) sessions."""
        try:
            session = self.Session()
            return session.query(SessionRecord).filter(
                SessionRecord.is_expired == False
            ).all()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to get active sessions: {str(e)}")

    def expire_old_sessions(self) -> int:
        """Expire sessions older than configured timeout."""
        try:
            session = self.Session()
            cutoff_time = datetime.utcnow() - timedelta(minutes=Config.SESSION_TIMEOUT)
            expired = session.query(SessionRecord).filter(
                SessionRecord.last_update < cutoff_time,
                SessionRecord.is_expired == False
            ).update({SessionRecord.is_expired: True})
            session.commit()
            return expired
        except SQLAlchemyError as e:
            session.rollback()
            raise RuntimeError(f"Failed to expire old sessions: {str(e)}")
