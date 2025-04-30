import uuid
import sqlalchemy
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .database import Base  # Import Base from models/database.py


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

    # Relationships (define relationship strings carefully)
    # Assumes AccessLog and VerificationImage classes will be defined and importable
    access_logs = relationship("AccessLog", back_populates="employee")
    verification_images_matched = relationship(
        "VerificationImage", back_populates="matched_employee")

    # Define indexes explicitly if needed, though index=True on column works for single columns
    # __table_args__ = (Index('employees_rfid_tag_idx', 'rfid_tag'), )
    # pgvector index needs to be created manually via SQL in init.sql

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.name}', rfid='{self.rfid_tag}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rfid_tag': self.rfid_tag,
            'role': self.role,
            'email': self.email,
            'photo_url': self.photo_url,
            'created_at': self.created_at,
            'active': self.active,
            'last_verified': self.last_verified,
            'verification_count': self.verification_count,
            'face_embedding': self.face_embedding
        }
