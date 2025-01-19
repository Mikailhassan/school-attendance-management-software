# teacher.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import TenantModel

class Teacher(TenantModel):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    name = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    date_of_joining = Column(Date, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    tsc_number = Column(String, nullable=True, unique=True)
    photo = Column(String, nullable=True)
    id_number = Column(Integer, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="teacher_profile")
    school = relationship("School", back_populates="teachers")
    attendances = relationship("TeacherAttendance", back_populates="teacher")

    def __repr__(self):
        return f"<Teacher(name={self.name}, tsc_number={self.tsc_number})>"