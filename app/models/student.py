# models/student.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    admission_number = Column(String, unique=True, nullable=False)  # Unique admission number for the student
    name = Column(String, nullable=False)                           # Full name of the student
    gender = Column(String, nullable=False)                         # Gender of the student
    class_name = Column(String, nullable=False)                     # Class/Grade student is in
    stream = Column(String, nullable=True)                          # Stream within the class
    date_of_joining = Column(Date, nullable=False)                  # Date of joining the school (DOJ)
    date_of_birth = Column(Date, nullable=False)                    # Date of birth (DOB)
    address = Column(String, nullable=True)                         # Home address of the student

    # Relationships
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False)  # Link to the parent
    parent = relationship("Parent", back_populates="children")             # Parent of the student

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)  # Link to the school
    school = relationship("School", back_populates="students")             # School associated with the student

    def __repr__(self):
        return f"<Student(name={self.name}, admission_number={self.admission_number})>"
