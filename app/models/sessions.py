from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)  # e.g. "Morning Session", "Afternoon Session"
    start_time = Column(Time, nullable=False)  
    end_time = Column(Time, nullable=False)    
    start_date = Column(Date, nullable=False)  
    end_date = Column(Date, nullable=False)    
    is_active = Column(Boolean, default=True)  
    description = Column(String, nullable=True)
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)

    # Relationships
    school = relationship("School", back_populates="sessions")
    student_attendances = relationship("StudentAttendance", back_populates="session")
    teacher_attendances = relationship("TeacherAttendance", back_populates="session")

    def __repr__(self):
        return f"<Session(name={self.name}, start_time={self.start_time}, end_time={self.end_time})>"