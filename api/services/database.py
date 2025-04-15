from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import logging
import sqlalchemy
import base64  # Added for image encoding

from sqlalchemy import create_engine, select, update  # Added select, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
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
        verification_image_id: Optional[uuid.UUID] = None,
        review_status: Optional[str] = None
    ) -> Optional[AccessLog]:
        """Logs an access attempt to the access_logs table."""
        session = self.Session()
        try:
            # Determine default status if not provided
            if review_status is None:
                review_status = 'approved' if access_granted else 'pending'

            # Create a new AccessLog record using the provided data
            log_entry = AccessLog(
                session_id=session_id,
                verification_method=verification_method,
                access_granted=access_granted,
                employee_id=employee_id,
                verification_confidence=verification_confidence,
                verification_image_path=str(
                    verification_image_id) if verification_image_id else None,
                review_status=review_status
            )
            session.add(log_entry)
            session.commit()
            logger.info(
                f"Logged access attempt for session {session_id}: Granted={access_granted}, Method={verification_method}, Status={review_status}")
            return log_entry
        except SQLAlchemyError as e:
            logger.error(
                f"Error logging access attempt for session {session_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    # Uses imported Notification and NotificationHistory models
    def save_notification_to_history(self, notification_data: dict) -> Optional[NotificationHistory]:
        """Saves notification data (as a dictionary) to the history table."""
        session = self.Session()
        try:
            # --- Extract data from the dictionary using key access ---
            notification_id = notification_data.get('id')
            user_id = notification_data.get('user_id')
            event_type = notification_data.get('event_type')
            severity = notification_data.get('severity')
            timestamp_str = notification_data.get('timestamp')
            session_id = notification_data.get('session_id')
            message = notification_data.get('message')
            image_url = notification_data.get('image_url')
            additional_data = notification_data.get('additional_data')
            status = notification_data.get('status')

            # --- Convert/Validate necessary fields ---
            history_id = None
            if notification_id:
                try:
                    history_id = uuid.UUID(notification_id)
                except ValueError:
                    logger.error(
                        f"Invalid UUID format for notification ID: {notification_id}. Generating new ID.")
                    history_id = uuid.uuid4()  # Generate new ID if provided is invalid
            else:
                logger.warning(
                    "No notification ID provided. Generating new ID for history.")
                history_id = uuid.uuid4()  # Generate new if missing

            user_uuid = None
            if user_id:
                try:
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    logger.warning(
                        f"Invalid UUID format for user_id in notification {history_id}: {user_id}. Storing as NULL.")

            timestamp_dt = None
            if timestamp_str:
                try:
                    # Pydantic v2 dumps datetime as isoformat string by default with mode='json'
                    timestamp_dt = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid timestamp format: {timestamp_str}. Using current time.")
                    timestamp_dt = datetime.utcnow()
            else:
                timestamp_dt = datetime.utcnow()

            # --- Create the history entry ---
            history_entry = NotificationHistory(
                id=history_id,
                event_type=event_type,  # Assumes these are already string values from enum dump
                severity=severity,     # Assumes these are already string values from enum dump
                timestamp=timestamp_dt,
                session_id=session_id,
                user_id=user_uuid,
                message=message,
                image_url=image_url,
                additional_data=additional_data,
                status=status
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

    # --- Admin Review Methods ---

    def get_pending_review_sessions(self) -> List[Dict]:
        """Retrieves access log entries pending manual review."""
        session = self.Session()
        try:
            stmt = (
                select(
                    AccessLog.id.label('log_id'),
                    AccessLog.session_id,
                    AccessLog.timestamp,
                    AccessLog.verification_method,
                    AccessLog.employee_id,
                    Employee.name.label('employee_name')  # Join to get name
                )
                # Use outer join in case employee_id is NULL
                .outerjoin(Employee, AccessLog.employee_id == Employee.id)
                .where(AccessLog.review_status == 'pending')
                .order_by(AccessLog.timestamp.asc())
            )
            results = session.execute(stmt).mappings().all()
            logger.info(f"Retrieved {len(results)} sessions pending review.")
            # Convert UUIDs to strings for JSON serialization
            pending_list = []
            for row in results:
                row_dict = dict(row)
                row_dict['log_id'] = str(row_dict['log_id'])
                if row_dict.get('employee_id'):
                    row_dict['employee_id'] = str(row_dict['employee_id'])
                pending_list.append(row_dict)
            return pending_list
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching pending review sessions: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_session_review_details(self, session_id: str) -> Optional[Dict]:
        """Retrieves detailed info for a specific session needing review."""
        session = self.Session()
        try:
            # Fetch access log entry
            log_stmt = select(AccessLog).where(
                AccessLog.session_id == session_id)
            access_log = session.execute(log_stmt).scalar_one_or_none()

            if not access_log:
                logger.warning(
                    f"No access log found for session_id: {session_id}")
                return None

            details = {
                "access_log": access_log,  # Return the SQLAlchemy model object
                "employee": None,
                "verification_images": [],
                "potential_matches": []  # Add this key even if empty
            }

            # Fetch associated employee if exists
            if access_log.employee_id:
                emp_stmt = select(Employee).where(
                    Employee.id == access_log.employee_id)
                details["employee"] = session.execute(
                    emp_stmt).scalar_one_or_none()

            # Fetch associated verification images and encode them
            img_stmt = select(VerificationImage).where(
                VerificationImage.session_id == session_id).order_by(VerificationImage.timestamp.asc())
            images = session.execute(img_stmt).scalars().all()
            for img in images:
                details["verification_images"].append({
                    "image_id": str(img.id),
                    "timestamp": img.timestamp.isoformat() if img.timestamp else None,
                    "image_data_b64": base64.b64encode(img.image_data).decode('utf-8') if img.image_data else None
                    # Add other image metadata if needed
                })

            # Fetch potential matches if it was a face-only attempt (example logic)
            if access_log.verification_method == "FACE_ONLY_PENDING_REVIEW":
                # Assuming the first image has the embedding used for the initial search
                # Check if embedding exists explicitly
                first_image_embedding = images[0].embedding if images and images[0].embedding is not None else None
                # Explicitly check if the embedding variable is not None
                if first_image_embedding is not None:
                    # Re-run similarity search or fetch stored results if available
                    # For simplicity, reusing find_similar_embeddings. Adjust threshold/limit as needed for review.
                    details["potential_matches"] = self.find_similar_embeddings(
                        first_image_embedding, threshold=0.7, limit=3)

            logger.info(f"Retrieved details for session review: {session_id}")
            return details

        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching details for session review {session_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def update_review_status(self, session_id: str, approved: bool, employee_id: Optional[str] = None) -> bool:
        """Updates the review status for a given session ID. Optionally updates the employee_id if provided (for Face-Only approvals)."""
        session = self.Session()
        try:
            new_status = 'approved' if approved else 'denied'
            values_to_update = {"review_status": new_status}

            # If approving and an employee_id is provided, add it to the update
            if approved and employee_id:
                try:
                    # Validate and convert to UUID if necessary
                    employee_uuid = uuid.UUID(employee_id)
                    values_to_update["employee_id"] = employee_uuid
                    logger.info(
                        f"Updating session {session_id} review status to '{new_status}' and setting employee_id to {employee_uuid}")
                except ValueError:
                    logger.error(
                        f"Invalid UUID format provided for employee_id: {employee_id}")
                    session.rollback()
                    return False
            else:
                logger.info(
                    f"Updating session {session_id} review status to '{new_status}'")

            stmt = (
                update(AccessLog)
                .where(AccessLog.session_id == session_id)
                # Only update if pending
                .where(AccessLog.review_status == 'pending')
                .values(**values_to_update)  # Use dictionary unpacking
                .execution_options(synchronize_session=False)
            )
            result = session.execute(stmt)

            if result.rowcount == 0:
                logger.warning(
                    f"Attempted to update review status for non-pending or non-existent session: {session_id}")
                session.rollback()  # Rollback if no rows affected
                return False

            session.commit()
            # logger.info(
            #     f"Updated review status for session {session_id} to '{new_status}'") # Covered by more specific logs above
            return True
        except SQLAlchemyError as e:
            logger.error(
                f"Error updating review status for session {session_id}: {e}", exc_info=True)
            session.rollback()
            return False
        finally:
            session.close()

    def get_access_log_by_session_id(self, session_id: str) -> Optional[AccessLog]:
        """Retrieves a single AccessLog record by its session_id."""
        session = self.Session()
        try:
            stmt = select(AccessLog).where(AccessLog.session_id == session_id)
            access_log = session.execute(stmt).scalar_one_or_none()
            if access_log:
                logger.debug(f"Found access log for session_id {session_id}")
            else:
                logger.debug(
                    f"No access log found for session_id {session_id}")
            return access_log
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching access log for session_id {session_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_verification_image_data(self, session_id: str) -> Optional[bytes]:
        """Retrieve the raw image data for a given session ID."""
        try:
            image_record = self.Session().query(VerificationImage.image_data)\
                .filter(VerificationImage.session_id == session_id)\
                .first()
            if image_record:
                return image_record.image_data
            else:
                return None
        except Exception as e:
            logger.error(
                f"Error retrieving verification image for session {session_id}: {e}", exc_info=True)
            return None
