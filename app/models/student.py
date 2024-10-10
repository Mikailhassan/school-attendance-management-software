from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    admission_number = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    stream = Column(String, nullable=True)
    date_of_joining = Column(Date, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    address = Column(String, nullable=True)

    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False)
    parent = relationship("Parent", back_populates="children")

    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    school = relationship("School", back_populates="students")

    def __repr__(self):
        return f"<Student(name={self.name}, admission_number={self.admission_number})>"
