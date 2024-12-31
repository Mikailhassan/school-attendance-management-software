# student.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import TenantModel

class Student(TenantModel):
    __tablename__ = "students"  # Changed from "student" to "students" for consistency

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    admission_number = Column(String, unique=True, nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)  # Added class_id
    stream_id = Column(Integer, ForeignKey('streams.id'), nullable=True)  # Made str
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('parents.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stream = relationship("Stream", back_populates="students")
    attendances = relationship("StudentAttendance", back_populates="student")
    school = relationship("School", back_populates="students")
    user = relationship("User", back_populates="student_profile")
    parent = relationship("Parent", back_populates="students")

    def __repr__(self):
        return f"<Student(name={self.name}, admission_number={self.admission_number}, form={self.form})>"
