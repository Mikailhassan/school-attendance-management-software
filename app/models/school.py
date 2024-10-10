from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from app.database import Base

class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)  # Added unique constraint
    address = Column(String, nullable=True)
    established_date = Column(Date, nullable=True)

    users = relationship("User", back_populates="school")
    classes = relationship("Class", back_populates="school")

    def __repr__(self):
        return f"<School(name={self.name})>"
