from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    form = Column(String, nullable=False)
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)

    school = relationship("School", back_populates="streams")
    students = relationship("Student", back_populates="stream")

    def __repr__(self):
        return f"<Stream(name={self.name}, form={self.form})>"
