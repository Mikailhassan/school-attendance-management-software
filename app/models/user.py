# models/user.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)                          # Full name of the user
    role = Column(String, nullable=False)                           # Role: super_admin, school_admin, teacher, student, parent
    password_hash = Column(String, nullable=False)                  # Password (hashed)
    is_active = Column(Boolean, default=True)                       # Is the user active?
    
    # Common fields for teachers and parents
    email = Column(String, unique=True, nullable=True)              # Email address for communication (for teachers, parents)
    phone = Column(String, nullable=True)                           # Phone number for SMS (for teachers, parents)
    
    # Teacher-specific fields
    tsc_number = Column(String, nullable=True)                      # Teacher Service Commission (TSC) number (only for teachers)
    
    # Student-specific fields
    admission_number = Column(String, unique=True, nullable=True)   # Unique admission number (only for students)
    date_of_birth = Column(Date, nullable=True)                     # Date of birth (DOB)

    # Foreign keys and relationships
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=True)  # Link to the school for relevant roles
    school = relationship("School", back_populates="users")               # School associated with this user

    # Fingerprint relationship
    fingerprint = relationship("Fingerprint", back_populates="user", uselist=False)  # Link to fingerprint record

    # Parent relationship (for parents linked to students)
    parent_profile = relationship("Parent", back_populates="user", uselist=False)  # Link to parent record

    # Other relationships (Teacher, Student)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)  # Link to teacher profile
    student_profile = relationship("Student", back_populates="user", uselist=False)  # Link to student profile

    def __repr__(self):
        return f"<User(name={self.name}, role={self.role})>"
