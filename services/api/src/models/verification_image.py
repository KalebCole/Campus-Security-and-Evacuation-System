import uuid
import sqlalchemy
from sqlalchemy import Column, DateTime, Boolean, Text, Float, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .database import Base


class VerificationImage(Base):
    """Model for the verification_images table."""
    __tablename__ = 'verification_images'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Text, nullable=False, index=True)
    storage_url = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True),
                       server_default=sqlalchemy.func.now(), index=True)
    processed = Column(Boolean, default=False)
    embedding = Column(Vector(512), nullable=True)
    confidence = Column(Float, nullable=True)
    matched_employee_id = Column(
        UUID(as_uuid=True), ForeignKey('employees.id'), nullable=True)
    device_id = Column(Text, nullable=False)

    matched_employee = relationship(
        "Employee", back_populates="verification_images_matched")

    def __repr__(self):
        return f"<VerificationImage(id={self.id}, session_id='{self.session_id}')>"
