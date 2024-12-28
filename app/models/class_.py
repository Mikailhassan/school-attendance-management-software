from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import TenantModel

class Class(TenantModel):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # e.g., "Grade 11"
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)

    # Relationships
    streams = relationship("Stream", back_populates="class_")
    school = relationship(
        "School", 
        back_populates="classes",
        single_parent=True
    )

    def __repr__(self):
        return f"<Class(name={self.name}, school_id={self.school_id})>"