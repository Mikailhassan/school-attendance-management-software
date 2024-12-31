from sqlalchemy import Column, String, JSON, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from app.schemas.school.requests import SchoolStatus

  

class School(Base):
    """
    School model with comprehensive attributes and relationships.
    This is the root of the tenant hierarchy.
    """
    __tablename__ = "schools"

    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Basic information
    name = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20), nullable=False)
    registration_number = Column(String(50), unique=True, nullable=False)
    school_type = Column(String(50), nullable=True) # e.g. 'Primary', 'Secondary', 'Tertiary'
    website = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default=SchoolStatus.ACTIVE)    
    # Location information
    address = Column(String(255), nullable=True)
    county = Column(String(255), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # School-specific configuration
    class_system = Column(String(50), nullable=False)
    class_range = Column(JSON, nullable=False)
    extra_info = Column(JSON, nullable=True)
    
    # Activity tracking
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # All relationships remain the same
    classes = relationship(
        "Class",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    students = relationship(
        "Student",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    teachers = relationship(
        "Teacher",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    parents = relationship(
        "Parent",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    streams = relationship(
        "Stream",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    student_attendance = relationship(
        "StudentAttendance",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    teacher_attendance = relationship(
        "TeacherAttendance",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    sessions = relationship(
        "Session",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    fingerprints = relationship(
        "Fingerprint",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )
    
    users = relationship(
        "User",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    revoked_tokens = relationship(
        "RevokedToken",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    def __repr__(self):
        return f"<School(name={self.name}, county={self.county}, class_system={self.class_system})>"