from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base

class School(Base):
    """School model representing an educational institution in the system."""
    
    __tablename__ = "schools"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=True)
    county = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    
    # School system details
    class_system = Column(String, nullable=True)  # e.g., '8-4-4', 'CBC'
    grade_range_start = Column(Integer, nullable=True)
    grade_range_end = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships with tenant models
    users = relationship("User", 
                        back_populates="school",
                        cascade="all, delete-orphan")
    
    students = relationship("Student", 
                          back_populates="school",
                          cascade="all, delete-orphan")
    
    teachers = relationship("Teacher", 
                          back_populates="school",
                          cascade="all, delete-orphan")
    
    streams = relationship("Stream", 
                         back_populates="school",
                         cascade="all, delete-orphan")
    
    parents = relationship("Parent", 
                         back_populates="school",
                         cascade="all, delete-orphan")
    
    attendances = relationship("Attendance", 
                             back_populates="school",
                             cascade="all, delete-orphan")
    
    fingerprints = relationship("Fingerprint", 
                              back_populates="school",
                              cascade="all, delete-orphan")
    
    revoked_tokens = relationship("RevokedToken",
                                back_populates="school",
                                cascade="all, delete-orphan")


    def __repr__(self):
        """String representation of School instance"""
        return f"<School(id={self.id}, name={self.name}, email={self.email})>"