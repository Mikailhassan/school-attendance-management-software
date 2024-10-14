from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship as orm_relationship
from sqlalchemy.sql import func
from app.database import Base
from .base import TenantModel

class Student(Base, TenantModel):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey('parents.id'))
    name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    admission_number = Column(String, unique=True, nullable=False)
    form = Column(String, nullable=False)
    stream_id = Column(Integer, ForeignKey('streams.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    school = orm_relationship("School", back_populates="students")
    stream = orm_relationship("Stream", back_populates="students")
    attendance_records = orm_relationship("Attendance", back_populates="user")
    user = orm_relationship("User", back_populates="student_profile")
    parent = orm_relationship("Parent", back_populates="students")

    def __repr__(self):
        return f"<Student(name={self.name}, admission_number={self.admission_number}, form={self.form}, stream={self.stream.name})>"