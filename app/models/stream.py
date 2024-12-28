from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import TenantModel

class Stream(TenantModel):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g., "North"
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)  # Link to the specific class
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)  # Link to the specific school

    # Relationships
    students = relationship("Student", back_populates="stream")
    school = relationship("School", back_populates="streams")
    class_ = relationship("Class", back_populates="streams")
    sessions = relationship("Session", back_populates="stream")  # Add this relationship

    def __repr__(self):
        return f"<Stream(name={self.name}, class_id={self.class_id}, school_id={self.school_id})>"
