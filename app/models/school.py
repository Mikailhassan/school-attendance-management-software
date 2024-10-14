from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)
    county = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    class_system = Column(String, nullable=True)  # Optional, e.g., '8-4-4', 'CBC'
    grade_range_start = Column(Integer, nullable=True)
    grade_range_end = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="school", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="school", cascade="all, delete-orphan")
    teachers = relationship("Teacher", back_populates="school", cascade="all, delete-orphan")
    streams = relationship("Stream", back_populates="school", cascade="all, delete-orphan")  # New relationship to Stream

    def __repr__(self):
        return f"<School(name={self.name}, email={self.email}, phone={self.phone})>"
