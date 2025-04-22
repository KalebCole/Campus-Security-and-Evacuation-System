import uuid
import sqlalchemy
from sqlalchemy import Column, DateTime, Boolean, Text, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base  # Import Base from models/database.py
# We need Employee for the relationship, but use a string reference to avoid circular imports initially
# from .employee import Employee


class AccessLog(Base):
    """Model for the access_logs table."""
    __tablename__ = 'access_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey(
        # Foreign key uses table.column name
        'employees.id'), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True),
                       server_default=sqlalchemy.func.now(), index=True)
    access_granted = Column(Boolean, nullable=False)
    verification_method = Column(Text, nullable=False)
    session_id = Column(Text, nullable=False)
    verification_confidence = Column(Float, nullable=True)
    verification_image_path = Column(
        Text, nullable=True)  # Changed in init.sql?
    review_status = Column(String(20), default='pending', nullable=False)

    # Relationship to Employee
    employee = relationship("Employee", back_populates="access_logs")

    def __repr__(self):
        return f"<AccessLog(id={self.id}, employee_id={self.employee_id}, granted={self.access_granted})>"
