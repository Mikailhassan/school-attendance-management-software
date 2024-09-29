# models/teacher.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)                 # Teacher's full name
    gender = Column(String, nullable=False)               # Gender of the teacher
    email = Column(String, unique=True, nullable=False)   # Email address for communication
    phone = Column(String, nullable=False)                # Phone number for SMS notifications
    date_of_joining = Column(Date, nullable=False)        # Date of joining the school (DOJ)
    date_of_birth = Column(Date, nullable=False)          # Date of birth (DOB)
    tsc_number = Column(String, nullable=False)           # Teacher Service Commission (TSC) number
    address = Column(String, nullable=True)               # Residential address

    # Relationships
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)  # Link to the school
    school = relationship("School", back_populates="teachers")             # School associated with the teacher

    def __repr__(self):
        return f"<Teacher(name={self.name}, tsc_number={self.tsc_number})>"
