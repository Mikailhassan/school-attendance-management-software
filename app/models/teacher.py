from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    date_of_joining = Column(Date, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    tsc_number = Column(String, nullable=False, unique=True)  # Added unique constraint
    address = Column(String, nullable=True)

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    school = relationship("School", back_populates="teachers")

    def __repr__(self):
        return f"<Teacher(name={self.name}, tsc_number={self.tsc_number})>"
