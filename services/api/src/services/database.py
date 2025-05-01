from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
import logging
import sqlalchemy
import base64  # Added for image encoding
from contextlib import contextmanager

# Added select, update, func
from sqlalchemy import create_engine, select, update, func
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import SQLAlchemyError
# Use relative imports
from ..core.config import Config
import uuid
from ..models.notification import Notification, NotificationHistory
from ..models.employee import Employee
from ..models.access_log import AccessLog
from ..models.verification_image import VerificationImage
from ..models.session_record import SessionRecord
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.declarative import declarative_base

# Setup logging
logger = logging.getLogger(__name__)

# Base definition removed
Base = declarative_base()

# --- SQLAlchemy Models Removed ---

# --- Database Service Class ---


class DatabaseService:
    """Service for handling database operations."""

    def __init__(self, connection_string: str):
        """Initialize database service with connection string."""
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=300,  # Recycle connections after 5 minutes
            pool_pre_ping=True  # Verify connection is still valid before using
        )
        # Configure sessionmaker with expire_on_commit=False
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        logger.info("Database service initialized successfully.")

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self):
        """Get a new session."""
        return self.Session()

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
    def find_similar_embeddings(self, new_embedding: List[float], threshold: float = 1 - Config.FACE_VERIFICATION_THRESHOLD, limit: int = 5) -> List[Dict]:
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

    # Modified to accept storage_url instead of image_data
    def save_verification_image(
        self,
        session_id: str,
        storage_url: str,  # Changed from image_data
        device_id: str,
        embedding: Optional[List[float]] = None,
        matched_employee_id: Optional[uuid.UUID] = None,
        confidence: Optional[float] = None,
        processed: bool = False,
        # Removed status parameter as it wasn't used consistently
    ) -> Optional[VerificationImage]:
        """Saves the verification image metadata (including storage URL) to the database."""
        with self.session_scope() as session:
            try:
                record = VerificationImage(  # Uses imported model
                    session_id=session_id,
                    storage_url=storage_url,  # Save the URL
                    device_id=device_id,
                    embedding=embedding,
                    matched_employee_id=matched_employee_id,
                    confidence=confidence,
                    processed=processed,
                    timestamp=datetime.utcnow().replace(tzinfo=None)
                )
                session.add(record)
                session.flush()  # Attempt to flush the insert
                session.refresh(record)  # Refresh to get the ID
                logger.info(
                    f"Saved verification image metadata {record.id} for session {session_id} with URL: {storage_url}")
                return record  # Return the newly created record

            except sqlalchemy.exc.IntegrityError as e:
                # Check if the error is specifically a unique constraint violation
                # for the session_id key in verification_images.
                # psycopg2 error code for unique violation is '23505'
                # We also check the constraint name for robustness.
                is_unique_violation = False
                if hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505':
                    if 'verification_images_session_id_key' in str(e.orig):
                        is_unique_violation = True

                if is_unique_violation:
                    # This specific error means the session ID already exists.
                    # This is likely due to a duplicate MQTT message arriving
                    # slightly later. We can treat this as non-fatal.
                    logger.warning(
                        f"Unique constraint violation for session_id '{session_id}' in verification_images. "
                        # Don't need full trace
                        f"Assuming duplicate message. Rollback and return None.", exc_info=False)
                    # Explicitly rollback *this* specific case before session_scope exits
                    session.rollback()
                    return None  # Indicate no *new* record was created
                else:
                    # If it's a different IntegrityError, re-raise it to be handled
                    # by the generic SQLAlchemyError handler below or the session_scope.
                    logger.error(
                        f"Unhandled IntegrityError saving verification image for session {session_id}: {e}", exc_info=True)
                    raise  # Re-raise the unexpected integrity error

            except SQLAlchemyError as e:
                # Catch any other database errors during the save operation.
                logger.error(
                    f"Error saving verification image metadata for session {session_id}: {e}", exc_info=True)
                # Rollback will be handled by session_scope context manager
                return None  # Indicate failure

    # Uses imported AccessLog model
    def log_access_attempt(
        self,
        session_id: str,
        verification_method: str,
        access_granted: bool,
        employee_id: Optional[uuid.UUID] = None,
        verification_confidence: Optional[float] = None,
        # Removed verification_image_id as it's linked via session_id now
        review_status: Optional[str] = None
    ) -> Optional[AccessLog]:
        """Logs an access attempt to the access_logs table."""
        with self.session_scope() as session:
            try:
                if review_status is None:
                    review_status = 'approved' if access_granted else 'pending'

                log_entry = AccessLog(
                    session_id=session_id,
                    verification_method=verification_method,
                    access_granted=access_granted,
                    employee_id=employee_id,
                    verification_confidence=verification_confidence,
                    # verification_image_path removed
                    review_status=review_status
                )
                session.add(log_entry)
                session.flush()  # Attempt to flush
                session.refresh(log_entry)
                logger.info(
                    f"Logged access attempt for session {session_id}: Granted={access_granted}, Method={verification_method}, Status={review_status}")
                return log_entry

            except sqlalchemy.exc.IntegrityError as e:
                session.rollback()  # Rollback the failed insert first
                is_unique_violation = False
                if hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505':
                    if 'access_logs_session_id_key' in str(e.orig):
                        is_unique_violation = True

                if is_unique_violation:
                    logger.warning(
                        f"Unique constraint violation for session_id '{session_id}' in access_logs. "
                        f"Attempting to update existing record.", exc_info=False)
                    try:
                        # Attempt to fetch the existing log entry
                        existing_log = session.query(AccessLog).filter(
                            AccessLog.session_id == session_id).one_or_none()

                        if existing_log:
                            # Update the existing entry with the new data
                            existing_log.verification_method = verification_method
                            existing_log.access_granted = access_granted
                            existing_log.employee_id = employee_id
                            existing_log.verification_confidence = verification_confidence
                            # Update review status only if it's different/relevant?
                            # Maybe prioritize 'pending' or 'denied' over 'approved'?
                            # Simple approach: overwrite with new status
                            existing_log.review_status = review_status or (
                                'approved' if access_granted else 'pending')
                            # Update timestamp to reflect the latest attempt
                            existing_log.timestamp = datetime.utcnow().replace(tzinfo=None)
                            session.commit()
                            logger.info(
                                f"Updated existing access log for session {session_id}")
                            return existing_log
                        else:
                            # This case shouldn't happen if it was a unique constraint error, but handle defensively
                            logger.error(
                                f"Unique constraint violation for session {session_id}, but failed to find existing record for update.")
                            return None
                    except SQLAlchemyError as update_err:
                        logger.error(
                            f"Error updating existing access log for session {session_id} after unique violation: {update_err}", exc_info=True)
                        session.rollback()  # Rollback the failed update
                        return None
                else:
                    # If it's a different IntegrityError, log and return None (or re-raise)
                    logger.error(
                        f"Unhandled IntegrityError logging access attempt for session {session_id}: {e}", exc_info=True)
                    # Let session_scope handle final rollback
                    return None  # Indicate failure

            except SQLAlchemyError as e:
                # Catch any other database errors during the logging.
                logger.error(
                    f"Error logging access attempt for session {session_id}: {e}", exc_info=True)
                # Rollback will be handled by session_scope context manager
                return None  # Indicate failure

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

    def _serialize_access_log(self, log: AccessLog, employee_name: Optional[str] = None, verification_image_url: Optional[str] = None) -> Dict[str, Any]:
        """Helper method to serialize an AccessLog model to a dictionary, including optional joined data."""
        if not log:
            return {}
        return {
            'id': str(log.id),
            'session_id': log.session_id,
            'timestamp': log.timestamp,
            'verification_method': log.verification_method,
            'review_status': log.review_status,
            'employee_id': str(log.employee_id) if log.employee_id else None,
            'access_granted': log.access_granted,
            'verification_confidence': log.verification_confidence,
            # Added fields from joins:
            'employee_name': employee_name,
            'verification_image_url': verification_image_url
        }

    def _serialize_employee(self, employee: Employee) -> Optional[Dict[str, Any]]:
        """Helper method to serialize an Employee model to a dictionary."""
        if not employee:
            return None
        return {
            'id': str(employee.id),
            'name': employee.name,
            'rfid_tag': employee.rfid_tag,
            'role': employee.role,
            'email': employee.email,
            'active': employee.active,
            'photo_url': employee.photo_url,  # This is the Supabase URL
            'last_verified': employee.last_verified,
            'verification_count': employee.verification_count,
            'created_at': employee.created_at
            # Exclude face_embedding for standard serialization
        }

    def get_pending_review_sessions(self) -> List[Dict[str, Any]]:
        """Get all pending review sessions with employee name and image URL."""
        with self.session_scope() as session:
            stmt = select(AccessLog, Employee.name, VerificationImage.storage_url).join(
                Employee, AccessLog.employee_id == Employee.id, isouter=True
            ).join(
                VerificationImage, AccessLog.session_id == VerificationImage.session_id, isouter=True
            ).where(
                AccessLog.review_status == 'pending'
            ).order_by(AccessLog.timestamp.desc())

            results = session.execute(stmt).all()
            # Process results: each item is a tuple (AccessLog, employee_name, storage_url)
            return [
                self._serialize_access_log(log, emp_name, img_url)
                for log, emp_name, img_url in results
            ]

    def get_todays_logs(self) -> List[Dict[str, Any]]:
        """Get all logs from today with employee name and image URL."""
        with self.session_scope() as session:
            today = date.today()
            stmt = select(AccessLog, Employee.name, VerificationImage.storage_url).join(
                Employee, AccessLog.employee_id == Employee.id, isouter=True
            ).join(
                VerificationImage, AccessLog.session_id == VerificationImage.session_id, isouter=True
            ).where(
                # Filter by today's date
                func.date(AccessLog.timestamp) == today,
                # Case-insensitive filter for status
                func.lower(AccessLog.review_status) != 'pending'
            ).order_by(AccessLog.timestamp.desc())

            results = session.execute(stmt).all()
            return [
                self._serialize_access_log(log, emp_name, img_url)
                for log, emp_name, img_url in results
            ]

    def get_previous_resolved_logs(self, page: int = 1, per_page: int = 10) -> Tuple[List[Dict[str, Any]], int]:
        """Get resolved logs with pagination, employee name, and image URL."""
        with self.session_scope() as session:
            # Base query for count and data
            base_query = select(AccessLog).where(
                AccessLog.review_status.in_(['approved', 'denied'])
            )

            # Get total count
            count_stmt = select(func.count(base_query.c.id))
            total = session.execute(count_stmt).scalar_one()

            # Get paginated results with joins
            stmt = select(AccessLog, Employee.name, VerificationImage.storage_url).join(
                Employee, AccessLog.employee_id == Employee.id, isouter=True
            ).join(
                VerificationImage, AccessLog.session_id == VerificationImage.session_id, isouter=True
            ).where(
                AccessLog.review_status.in_(['approved', 'denied'])
            ).order_by(AccessLog.timestamp.desc()).offset(
                (page - 1) * per_page
            ).limit(per_page)

            results = session.execute(stmt).all()
            serialized_results = [
                self._serialize_access_log(log, emp_name, img_url)
                for log, emp_name, img_url in results
            ]
            return serialized_results, total

    # Modified to return storage_url directly
    def get_session_review_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific session review, including the image storage URL."""
        with self.session_scope() as session:
            try:
                log_stmt = select(AccessLog).where(
                    AccessLog.session_id == session_id)
                access_log = session.execute(log_stmt).scalar_one_or_none()
                if not access_log:
                    return None

                # Fetch verification image metadata (including URL)
                image_stmt = select(VerificationImage).where(
                    VerificationImage.session_id == session_id)
                verification_image = session.execute(
                    image_stmt).scalar_one_or_none()
                image_url = verification_image.storage_url if verification_image else None  # Get URL

                employee = None
                if access_log.employee_id:
                    emp_stmt = select(Employee).where(
                        Employee.id == access_log.employee_id)
                    employee = session.execute(emp_stmt).scalar_one_or_none()

                potential_matches = []
                if access_log.verification_method == 'FACE_ONLY_PENDING_REVIEW' and verification_image is not None and verification_image.embedding is not None:
                    potential_matches = self.find_similar_embeddings(
                        verification_image.embedding)

                # Serialize employee data using the helper
                employee_data = self._serialize_employee(employee)

                # Solution 1: Check if employee exists before accessing name for serialization
                employee_name_for_log = employee.name if employee else None

                return {
                    'access_log': self._serialize_access_log(access_log, employee_name_for_log, image_url),
                    'verification_image_url': image_url,  # Direct Supabase URL
                    'employee': employee_data,
                    'potential_matches': potential_matches
                }
            except Exception as e:
                logger.error(
                    f"Error getting session review details for {session_id}: {e}", exc_info=True)
                return None

    def get_access_log_by_session_id(self, session_id: str) -> Optional[AccessLog]:
        """Get an access log by session ID."""
        with self.session_scope() as session:
            stmt = select(AccessLog).where(AccessLog.session_id == session_id)
            return session.execute(stmt).scalar_one_or_none()

    def update_review_status(self, session_id: str, approved: bool, employee_id: Optional[str] = None) -> bool:
        """Update the review status of an access log."""
        with self.session_scope() as session:
            try:
                stmt = select(AccessLog).where(
                    AccessLog.session_id == session_id)
                access_log = session.execute(stmt).scalar_one_or_none()

                if not access_log or access_log.review_status != 'pending':
                    return False

                access_log.review_status = 'approved' if approved else 'denied'
                if employee_id and approved:
                    access_log.employee_id = employee_id
                    access_log.access_granted = True

                session.commit()
                return True
            except SQLAlchemyError as e:
                logger.error(f"Database error updating review status: {e}")
                session.rollback()
                return False

    # --- Employee Management Methods (Milestone 10 & 11) ---

    def get_all_employees(self, include_inactive: bool = False) -> List[Employee]:
        """Retrieves all employee records, optionally including inactive ones."""
        with self.session_scope() as session:
            try:
                stmt = select(Employee).order_by(Employee.name.asc())
                if not include_inactive:
                    stmt = stmt.where(Employee.active == True)
                employees = session.execute(stmt).scalars().all()
                logger.info(f"Retrieved {len(employees)} employee records.")
                return employees
            except SQLAlchemyError as e:
                logger.error(
                    f"Error fetching all employees: {e}", exc_info=True)
                return []

    # Modified create_employee to use session_scope and handle potential None photo_url
    def create_employee(
        self,
        name: str,
        rfid_tag: str,
        role: str,
        email: str,
        active: bool = True,
        face_embedding: Optional[List[float]] = None,  # Added embedding
        photo_url: Optional[str] = None  # Added photo_url (Supabase URL)
    ) -> Optional[Employee]:
        """Creates a new employee record including optional embedding and photo URL."""
        with self.session_scope() as session:
            try:
                new_employee = Employee(
                    name=name,
                    rfid_tag=rfid_tag,
                    role=role,
                    email=email,
                    active=active,
                    face_embedding=face_embedding,
                    photo_url=photo_url
                )
                session.add(new_employee)
                session.flush()
                session.refresh(new_employee)
                logger.info(
                    f"Successfully created employee {new_employee.id} ({name}).")
                return new_employee
            except sqlalchemy.exc.IntegrityError as ie:
                logger.warning(
                    f"Integrity error creating employee {name}: {ie}", exc_info=False)
                # Let session_scope handle rollback
                return None  # Indicate failure
            except SQLAlchemyError as e:
                logger.error(
                    f"Error creating employee {name}: {e}", exc_info=True)
                # Let session_scope handle rollback
                return None

    def get_employee_by_id(self, employee_id: uuid.UUID) -> Optional[Employee]:
        """Retrieves a single employee record by their UUID."""
        with self.session_scope() as session:
            try:
                employee = session.get(Employee, employee_id)
                if employee:
                    logger.debug(f"Found employee {employee_id}")
                else:
                    logger.warning(
                        f"Employee not found with ID: {employee_id}")
                return employee
            except SQLAlchemyError as e:
                logger.error(
                    f"Error fetching employee by ID {employee_id}: {e}", exc_info=True)
                return None

    # Modified update_employee to use session_scope
    def update_employee(self, employee_id: uuid.UUID, data: Dict[str, Any]) -> Optional[Employee]:
        """Updates an existing employee record with the provided data."""
        with self.session_scope() as session:
            try:
                employee = session.get(Employee, employee_id)
                if not employee:
                    logger.warning(
                        f"Cannot update non-existent employee {employee_id}")
                    return None

                allowed_fields = {'name', 'rfid_tag', 'role',
                                  'email', 'active', 'photo_url', 'face_embedding'}
                updated_fields = []
                for key, value in data.items():
                    if key in allowed_fields and hasattr(employee, key):
                        setattr(employee, key, value)
                        updated_fields.append(key)

                if not updated_fields:
                    logger.info(
                        f"No valid fields provided to update for employee {employee_id}")
                    return employee  # Return existing if no changes

                # session.commit() handled by scope
                session.flush()
                session.refresh(employee)
                logger.info(
                    f"Successfully updated employee {employee_id}. Fields: {updated_fields}")
                return employee
            except sqlalchemy.exc.IntegrityError as ie:
                logger.warning(
                    f"Integrity error updating employee {employee_id}: {ie}", exc_info=False)
                # Rollback handled by scope
                return None  # Indicate failure
            except SQLAlchemyError as e:
                logger.error(
                    f"Error updating employee {employee_id}: {e}", exc_info=True)
                # Rollback handled by scope
                return None

    # Modified delete_employee to use session_scope
    def delete_employee(self, employee_id: uuid.UUID) -> bool:
        """Deletes an employee record by their UUID."""
        with self.session_scope() as session:
            try:
                employee = session.get(Employee, employee_id)
                if not employee:
                    logger.warning(
                        f"Cannot delete non-existent employee {employee_id}")
                    return False

                # Optional: Delete associated Supabase object here before DB delete
                # if employee.photo_url:
                #    try:
                #        # extract filename/path from URL
                #        # call supabase_client.storage.from_(...).remove([path])
                #    except Exception as storage_delete_err:
                #        logger.error(f"Failed to delete Supabase object for employee {employee_id}: {storage_delete_err}")
                #        # Decide whether to proceed with DB delete? Maybe not.
                #        # return False

                session.delete(employee)
                # session.commit() handled by scope
                logger.info(
                    f"Successfully deleted employee {employee_id} ({employee.name}).")
                return True
            except SQLAlchemyError as e:
                logger.error(
                    f"Error deleting employee {employee_id}: {e}", exc_info=True)
                # Rollback handled by scope
                return False

    # Keep create_employee_with_session and save_verification_image_with_session
    # but ensure they use storage_url instead of image_data/local paths
    def create_employee_with_session(
        self,
        session,
        name: str,
        rfid_tag: str,
        role: str,
        email: str,
        active: bool = True,
        face_embedding: Optional[List[float]] = None,
        photo_url: Optional[str] = None,  # Supabase URL
        last_verified: Optional[datetime] = None,
        verification_count: int = 0
    ) -> Optional[Employee]:
        # ... (Implementation mostly the same, just ensure photo_url is used correctly)
        try:
            new_employee = Employee(
                name=name, rfid_tag=rfid_tag, role=role, email=email, active=active,
                face_embedding=face_embedding, photo_url=photo_url,  # Use Supabase URL
                last_verified=last_verified, verification_count=verification_count
            )
            session.add(new_employee)
            session.flush()
            logger.info(f"Employee {new_employee.id} added to session.")
            return new_employee
        except Exception as e:  # Catch broad exception to handle potential issues
            logger.error(
                f"Error creating employee in session: {e}", exc_info=True)
            raise  # Re-raise to allow rollback

    def save_verification_image_with_session(
        self,
        session,
        session_id: str,
        storage_url: str,  # Changed from image_data
        device_id: str,
        embedding: Optional[List[float]] = None,
        matched_employee_id: Optional[uuid.UUID] = None,
        confidence: Optional[float] = None,
        processed: bool = False
        # Removed status parameter
    ) -> Optional[VerificationImage]:
        # ... (Implementation mostly the same, use storage_url)
        try:
            record = VerificationImage(
                session_id=session_id, storage_url=storage_url, device_id=device_id,  # Use URL
                embedding=embedding, matched_employee_id=matched_employee_id,
                confidence=confidence, processed=processed,
                timestamp=datetime.utcnow().replace(tzinfo=None)
            )
            session.add(record)
            session.flush()
            logger.info(
                f"Verification image metadata for session {session_id} added to session.")
            return record
        except Exception as e:
            logger.error(
                f"Error saving verification image metadata in session: {e}", exc_info=True)
            raise

    def check_session_exists(self, session_id: str) -> bool:
        """Checks if a session ID exists in either access_logs or verification_images."""
        with self.session_scope() as session:
            try:
                # Check access_logs
                log_exists_stmt = select(AccessLog.id).where(
                    AccessLog.session_id == session_id).limit(1)
                log_exists = session.execute(
                    log_exists_stmt).scalar() is not None
                if log_exists:
                    logger.debug(
                        f"Session ID {session_id} found in access_logs.")
                    return True

                # Check verification_images
                image_exists_stmt = select(VerificationImage.id).where(
                    VerificationImage.session_id == session_id).limit(1)
                image_exists = session.execute(
                    image_exists_stmt).scalar() is not None
                if image_exists:
                    logger.debug(
                        f"Session ID {session_id} found in verification_images.")
                    return True

                # If not found in either
                logger.debug(
                    f"Session ID {session_id} not found in relevant tables.")
                return False
            except SQLAlchemyError as e:
                logger.error(
                    f"Error checking for session ID {session_id}: {e}", exc_info=True)
                # In case of error, assume it might exist to be safe?
                # Or return False and rely on constraints? Returning False seems reasonable.
                return False
