from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import sqlalchemy

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Text, Float, Integer, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from pgvector.sqlalchemy import Vector
from config import Config
import uuid

# Setup logging
logger = logging.getLogger(__name__)

Base = declarative_base()

# --- SQLAlchemy Models ---


class Employee(Base):
    """Model for the employees table."""
    __tablename__ = 'employees'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    rfid_tag = Column(Text, unique=True, nullable=False, index=True)
    role = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    face_embedding = Column(Vector(512))  # Dimension from init.sql
    created_at = Column(DateTime(timezone=True),
                        server_default=sqlalchemy.func.now())
    active = Column(Boolean, default=True)
    last_verified = Column(DateTime(timezone=True), nullable=True)
    verification_count = Column(Integer, default=0)
    photo_url = Column(Text, nullable=True)

    # Relationships (optional but good practice)
    access_logs = relationship("AccessLog", back_populates="employee")
    verification_images_matched = relationship(
        "VerificationImage", back_populates="matched_employee")


class AccessLog(Base):
    """Model for the access_logs table."""
    __tablename__ = 'access_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey(
        'employees.id'), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True),
                       server_default=sqlalchemy.func.now(), index=True)
    access_granted = Column(Boolean, nullable=False)
    verification_method = Column(Text, nullable=False)
    # Assuming session_id might not always be a UUID
    session_id = Column(Text, nullable=False)
    verification_confidence = Column(Float, nullable=True)
    # Path if storing images externally
    verification_image_path = Column(Text, nullable=True)

    # Relationship
    employee = relationship("Employee", back_populates="access_logs")


class VerificationImage(Base):
    """Model for the verification_images table."""
    __tablename__ = 'verification_images'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Text, nullable=False, index=True)
    # Use LargeBinary for BYTEA
    image_data = Column(LargeBinary, nullable=False)
    timestamp = Column(DateTime(timezone=True),
                       server_default=sqlalchemy.func.now(), index=True)
    processed = Column(Boolean, default=False)
    embedding = Column(Vector(512), nullable=True)
    confidence = Column(Float, nullable=True)
    matched_employee_id = Column(
        UUID(as_uuid=True), ForeignKey('employees.id'), nullable=True)
    device_id = Column(Text, nullable=False)

    # Relationship
    matched_employee = relationship(
        "Employee", back_populates="verification_images_matched")


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


# --- Database Service Class ---

class DatabaseService:
    """Service for handling database operations."""

    def __init__(self, connection_string: str):
        """Initialize database service."""
        try:
            self.engine = create_engine(connection_string)
            # In SQLAlchemy 2.0, create_all is typically called separately or managed by migration tools
            # Base.metadata.create_all(self.engine) # Consider moving this or using Alembic
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database service initialized successfully.")
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to initialize database: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize database: {str(e)}")

    # --- Session Methods (Existing) ---
    def create_session(self, device_id: str, state: str) -> Optional[SessionRecord]:
        """Create a new session record."""
        session = self.Session()
        try:
            now = datetime.utcnow().replace(tzinfo=None)
            record = SessionRecord(
                device_id=device_id,
                state=state,
                start_time=now,
                last_update=now
            )
            session.add(record)
            session.commit()
            logger.info(
                f"Created session record {record.id} for device {device_id}")
            return record
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to create session for device {device_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def update_session(self, session_id: uuid.UUID, state: str,
                       face_detected: bool = None, rfid_detected: bool = None) -> Optional[SessionRecord]:
        """Update an existing session record."""
        session = self.Session()
        try:
            # Use SQLAlchemy 2.0 style query
            record = session.get(SessionRecord, session_id)
            if record:
                record.state = state
                record.last_update = datetime.utcnow().replace(tzinfo=None)
                if face_detected is not None:
                    record.face_detected = face_detected
                if rfid_detected is not None:
                    record.rfid_detected = rfid_detected
                session.commit()
                logger.debug(
                    f"Updated session record {session_id} to state {state}")
                return record
            else:
                logger.warning(
                    f"Attempted to update non-existent session {session_id}")
                return None
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to update session {session_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def get_active_sessions(self) -> List[SessionRecord]:
        """Get all active (non-expired) sessions."""
        session = self.Session()
        try:
            # Use SQLAlchemy 2.0 style query
            stmt = sqlalchemy.select(SessionRecord).where(
                SessionRecord.is_expired == False)
            results = session.execute(stmt).scalars().all()
            logger.debug(f"Retrieved {len(results)} active sessions.")
            return results
        except SQLAlchemyError as e:
            logger.error(f"Failed to get active sessions: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def expire_old_sessions(self) -> Optional[int]:
        """Expire sessions older than configured timeout."""
        session = self.Session()
        try:
            cutoff_time = datetime.utcnow().replace(tzinfo=None) - \
                timedelta(minutes=Config.SESSION_TIMEOUT)
            # gets all sessions that are not expired and are older than the cutoff time
            stmt = sqlalchemy.update(SessionRecord).where(SessionRecord.last_update < cutoff_time, SessionRecord.is_expired == False).values(
                is_expired=True).execution_options(synchronize_session=False)
            # execute options is used to prevent the session from being committed to the database
            # this is because the session is being updated in the same session

            result = session.execute(stmt)
            session.commit()
            expired_count = result.rowcount
            if expired_count > 0:
                logger.info(f"Expired {expired_count} old sessions.")
            return expired_count
        except SQLAlchemyError as e:
            logger.error(f"Failed to expire old sessions: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    # --- New Methods for Face Matching ---

    def get_employee_by_rfid(self, rfid_tag: str) -> Optional[Employee]:
        """Retrieves an employee record based on their RFID tag."""
        session = self.Session()
        try:
            stmt = sqlalchemy.select(Employee).where(
                Employee.rfid_tag == rfid_tag)
            employee = session.execute(stmt).scalar_one_or_none()
            if employee:
                logger.debug(
                    f"Found employee {employee.id} for RFID tag {rfid_tag}")
            else:
                logger.debug(f"No employee found for RFID tag {rfid_tag}")
            return employee
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching employee by RFID {rfid_tag}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def find_similar_embeddings(self, new_embedding: List[float], threshold: float = 0.6, limit: int = 5) -> List[Dict]:
        """Finds employees with face embeddings similar to the new one using cosine distance.

        Args:
            new_embedding: The embedding vector (list of floats) to search for.
            threshold: The maximum cosine distance (lower is more similar). E.g., 0.6
            limit: The maximum number of results to return.

        Returns:
            A list of dictionaries, each containing 'employee_id', 'name', 'distance',
            and 'confidence' (1 - distance), ordered by similarity.
        """
        session = self.Session()
        try:
            # Note: <-> operator calculates cosine distance in pgvector
            # Cosine Distance = 1 - Cosine Similarity
            stmt = sqlalchemy.select(
                Employee.id.label('employee_id'),
                Employee.name,
                Employee.face_embedding.cosine_distance(
                    new_embedding).label('distance')
            ).filter(Employee.face_embedding.cosine_distance(new_embedding)
                     < threshold).order_by(sqlalchemy.asc('distance')).limit(limit)

            # Use .mappings() for dict-like results
            results = session.execute(stmt).mappings().all()

            matches = [
                {
                    "employee_id": r["employee_id"],
                    "name": r["name"],
                    "distance": r["distance"],
                    # Convert distance to similarity
                    "confidence": 1.0 - r["distance"]
                }
                for r in results
            ]
            logger.debug(
                f"Found {len(matches)} similar embeddings below distance {threshold}")
            return matches
        except SQLAlchemyError as e:
            logger.error(
                f"Error finding similar embeddings: {e}", exc_info=True)
            return []
        except Exception as e:
            # Catch potential pgvector-specific errors if any arise separately
            logger.error(
                f"Unexpected error during embedding search: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def save_verification_image(
        self,
        session_id: str,
        image_data: bytes,
        device_id: str,
        embedding: Optional[List[float]] = None,
        matched_employee_id: Optional[uuid.UUID] = None,
        confidence: Optional[float] = None,
        processed: bool = False
    ) -> Optional[VerificationImage]:
        """Saves the verification image data and metadata to the database."""
        session = self.Session()
        try:
            record = VerificationImage(
                session_id=session_id,
                image_data=image_data,
                device_id=device_id,
                embedding=embedding,
                matched_employee_id=matched_employee_id,
                confidence=confidence,
                processed=processed,
                timestamp=datetime.utcnow().replace(tzinfo=None)
            )
            session.add(record)
            session.commit()
            logger.info(
                f"Saved verification image {record.id} for session {session_id}")
            return record
        except SQLAlchemyError as e:
            logger.error(
                f"Error saving verification image for session {session_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    # --- New Method for Logging Access ---

    def log_access_attempt(
        self,
        session_id: str,
        verification_method: str,
        access_granted: bool,
        employee_id: Optional[uuid.UUID] = None,
        verification_confidence: Optional[float] = None,
        # Matches TEXT field in schema
        verification_image_path: Optional[str] = None
    ) -> Optional[AccessLog]:
        """Logs an access attempt to the access_logs table."""
        session = self.Session()
        try:
            # Create a new AccessLog record using the provided data
            log_entry = AccessLog(
                session_id=session_id,
                verification_method=verification_method,
                access_granted=access_granted,
                employee_id=employee_id,  # Can be None
                verification_confidence=verification_confidence,  # Can be None
                verification_image_path=verification_image_path,  # Can be None
                # timestamp is handled by server_default in the model/db
            )
            session.add(log_entry)
            session.commit()
            logger.info(
                f"Logged access attempt for session {session_id}: Granted={access_granted}, Method={verification_method}")
            return log_entry
        except SQLAlchemyError as e:
            logger.error(
                f"Error logging access attempt for session {session_id}: {e}", exc_info=True)
            session.rollback()  # Rollback on error
            return None
        finally:
            session.close()  # Ensure session is closed
