from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import TenantModel

class Class(TenantModel):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g., "Grade 11"

    # Relationships
    streams = relationship("Stream", back_populates="class_")
    school = relationship("School", back_populates="classes")

    def __repr__(self):
        return f"<Class(name={self.name}, school_id={self.school_id})>"