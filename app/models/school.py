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
    
    # Location information
    address = Column(String(255), nullable=True)
    county = Column(String(255), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # School-specific configuration
    class_system = Column(String(50), nullable=False)
    class_range = Column(JSON, nullable=False)
    extra_info = Column(JSON, nullable=True)

    # Relationships
    classes = relationship(
        "Class",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    students = relationship(
        "Student",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    teachers = relationship(
        "Teacher",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    parents = relationship(
        "Parent",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    streams = relationship(
        "Stream",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    student_attendance = relationship(
        "StudentAttendance",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    teacher_attendance = relationship(
        "TeacherAttendance",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    sessions = relationship(
        "Session",
        back_populates="school",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        return f"<School(name={self.name}, county={self.county}, class_system={self.class_system})>"