from sqlalchemy import Column, String, JSON, Integer
from sqlalchemy.orm import relationship
from .base import Base

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
    
    # Location information
    address = Column(String(255), nullable=True)
    county = Column(String(255), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # School-specific configuration
    class_system = Column(String(50), nullable=False)
    class_range = Column(JSON, nullable=False)
    extra_info = Column(JSON, nullable=True)

    # Class relationship - maps to Class model
    classes = relationship(
        "Class",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Student relationship
    students = relationship(
        "Student",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Teacher relationship
    teachers = relationship(
        "Teacher",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Parent relationship
    parents = relationship(
        "Parent",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Stream relationship
    streams = relationship(
        "Stream",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Student Attendance relationship - maps to StudentAttendance which inherits from AttendanceBase
    student_attendance = relationship(
        "StudentAttendance",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Teacher Attendance relationship - maps to TeacherAttendance which inherits from AttendanceBase
    teacher_attendance = relationship(
        "TeacherAttendance",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Session relationship
    sessions = relationship(
        "Session",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # Fingerprint relationship
    fingerprints = relationship(
        "Fingerprint",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy='select'
    )

    # User relationship (if users are school-specific)
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