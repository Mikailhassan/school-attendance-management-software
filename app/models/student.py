from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import TenantModel

class Student(TenantModel):
    __tablename__ = "student"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    admission_number = Column(String, unique=True, nullable=False)
    form = Column(String, nullable=False)
    stream_id = Column(Integer, ForeignKey('streams.id'))
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('parents.id'), nullable=False)  # Add this line
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stream = relationship("Stream", back_populates="students")
    attendances = relationship("Attendance", back_populates="student")
    school = relationship("School", back_populates="students")
    user = relationship("User", back_populates="student_profile")
    parent = relationship("Parent", back_populates="students")  # Add this line

    def __repr__(self):
        return f"<Student(name={self.name}, admission_number={self.admission_number}, form={self.form})>"