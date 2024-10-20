from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import TenantModel

class Teacher(TenantModel):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)
    name = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    date_of_joining = Column(Date, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    tsc_number = Column(String, nullable=False, unique=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="teacher_profile")
    school = relationship("School", back_populates="teachers")  # Add this line

    def __repr__(self):
        return f"<Teacher(name={self.name}, tsc_number={self.tsc_number})>"
