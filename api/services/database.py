from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import sqlalchemy

from sqlalchemy import create_engine
# Removed Column, String etc. as they are only used in models now
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
# Removed Vector import
from config import Config
import uuid
# Updated model imports
from models.notification import Notification, NotificationHistory
from models.employee import Employee
from models.access_log import AccessLog
from models.verification_image import VerificationImage
from models.session_record import SessionRecord  # Added SessionRecord import

# Setup logging
logger = logging.getLogger(__name__)

# Base definition removed

# --- SQLAlchemy Models Removed ---

# --- Database Service Class ---


class DatabaseService:
    """Service for handling database operations."""

    def __init__(self, connection_string: str):
        """Initialize database service."""
        try:
            self.engine = create_engine(connection_string)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database service initialized successfully.")
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to initialize database: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize database: {str(e)}")

    # --- Session Methods ---
    # Now uses imported SessionRecord model
    def create_session(self, device_id: str, state: str) -> Optional[SessionRecord]:
        """Create a new session record."""
        session = self.Session()
        try:
            now = datetime.utcnow().replace(tzinfo=None)
            record = SessionRecord(  # Uses imported model
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

    # Uses imported SessionRecord model
    def update_session(self, session_id: uuid.UUID, state: str,
                       face_detected: bool = None, rfid_detected: bool = None) -> Optional[SessionRecord]:
        """Update an existing session record."""
        session = self.Session()
        try:
            # Use SQLAlchemy 2.0 style query
            # Uses imported model
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

    # Uses imported SessionRecord model
    def get_active_sessions(self) -> List[SessionRecord]:
        """Get all active (non-expired) sessions."""
        session = self.Session()
        try:
            # Use SQLAlchemy 2.0 style query
            stmt = sqlalchemy.select(SessionRecord).where(  # Uses imported model
                SessionRecord.is_expired == False)
            results = session.execute(stmt).scalars().all()
            logger.debug(f"Retrieved {len(results)} active sessions.")
            return results
        except SQLAlchemyError as e:
            logger.error(f"Failed to get active sessions: {e}", exc_info=True)
            return []
        finally:
            session.close()

    # Uses imported SessionRecord model
    def expire_old_sessions(self) -> Optional[int]:
        """Expire sessions older than configured timeout."""
        session = self.Session()
        try:
            cutoff_time = datetime.utcnow().replace(tzinfo=None) - \
                timedelta(minutes=Config.SESSION_TIMEOUT)
            # gets all sessions that are not expired and are older than the cutoff time
            stmt = sqlalchemy.update(SessionRecord).where(SessionRecord.last_update < cutoff_time, SessionRecord.is_expired == False).values(  # Uses imported model
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

    # --- Methods using other imported models ---

    # Uses imported Employee model
    def get_employee_by_rfid(self, rfid_tag: str) -> Optional[Employee]:
        """Retrieves an employee record based on their RFID tag."""
        session = self.Session()
        try:
            stmt = sqlalchemy.select(Employee).where(  # Uses imported model
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

    # Uses imported Employee model
    def find_similar_embeddings(self, new_embedding: List[float], threshold: float = 0.6, limit: int = 5) -> List[Dict]:
        """Finds employees with face embeddings similar to the new one using cosine distance."""
        session = self.Session()
        try:
            # Note: <-> operator calculates cosine distance in pgvector
            # Cosine Distance = 1 - Cosine Similarity
            stmt = sqlalchemy.select(
                Employee.id.label('employee_id'),
                Employee.name,
                Employee.face_embedding.cosine_distance(  # Uses imported model
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

    # Uses imported VerificationImage model
    def save_verification_image(
        self,
        session_id: str,
        image_data: bytes,
        device_id: str,
        embedding: Optional[List[float]] = None,
        matched_employee_id: Optional[uuid.UUID] = None,
        confidence: Optional[float] = None,
        processed: bool = False,
        status: Optional[str] = None
    ) -> Optional[VerificationImage]:
        """Saves the verification image data and metadata to the database."""
        session = self.Session()
        try:
            record = VerificationImage(  # Uses imported model
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

    # Uses imported AccessLog model
    def log_access_attempt(
        self,
        session_id: str,
        verification_method: str,
        access_granted: bool,
        employee_id: Optional[uuid.UUID] = None,
        verification_confidence: Optional[float] = None,
        verification_image_id: Optional[uuid.UUID] = None
    ) -> Optional[AccessLog]:  # Changed return type hint
        """Logs an access attempt to the access_logs table."""
        session = self.Session()
        try:
            # Create a new AccessLog record using the provided data
            log_entry = AccessLog(  # Uses imported model
                session_id=session_id,
                verification_method=verification_method,
                access_granted=access_granted,
                employee_id=employee_id,  # Can be None
                verification_confidence=verification_confidence,  # Can be None
                verification_image_path=str(
                    verification_image_id) if verification_image_id else None,  # Store UUID as string?
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

    # Uses imported Notification and NotificationHistory models
    def save_notification_to_history(self, notification: Notification) -> Optional[NotificationHistory]:
        """Saves a notification object to the history table."""
        session = self.Session()
        try:
            # Convert user_id string from Notification dataclass to UUID if necessary
            user_uuid = None
            if notification.user_id:
                try:
                    user_uuid = uuid.UUID(notification.user_id)
                except ValueError:
                    logger.warning(
                        f"Invalid UUID format for user_id in notification {notification.id}: {notification.user_id}")

            history_entry = NotificationHistory(  # Uses imported model
                id=uuid.UUID(notification.id),  # Use the same UUID
                event_type=notification.event_type.value,
                severity=notification.severity.value,
                # Convert ISO string back to datetime
                timestamp=datetime.fromisoformat(notification.timestamp),
                session_id=notification.session_id,
                user_id=user_uuid,
                message=notification.message,
                image_url=notification.image_url,
                additional_data=notification.additional_data,
                status=notification.status  # Use the status from the notification object
            )
            session.add(history_entry)
            session.commit()
            session.refresh(history_entry)
            logger.info(f"Saved notification to history: {history_entry.id}")
            return history_entry
        except Exception as e:
            logger.error(
                f"Error saving notification to history: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()
