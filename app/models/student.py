from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import TenantModel
from enum import Enum as PyEnum

class Student(TenantModel):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    photo = Column(String, nullable=True) 
    admission_number = Column(String, unique=True, nullable=False)
    gender = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=False)  
    date_of_joining = Column(Date, nullable=True) 
    address = Column(Text, nullable=True)
    fingerprint = Column(String, nullable=True)
    id_number = Column(String, nullable=True)  
    
    # Existing foreign keys
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    stream_id = Column(Integer, ForeignKey('streams.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('parents.id'), nullable=False)
    
    
    
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Preserved all existing relationships
    student_class = relationship("Class", back_populates="students")
    stream = relationship("Stream", back_populates="students")
    attendances = relationship("StudentAttendance", back_populates="student")
    school = relationship("School", back_populates="students")
    user = relationship("User", back_populates="student_profile")
    parent = relationship("Parent", back_populates="students")

    def __repr__(self):
        return f"<Student({id(self)})>"