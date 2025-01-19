from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship, declared_attr
from .attendance_base import AttendanceBase

class StudentAttendance(AttendanceBase):
    """
    Attendance record specific to students.
    """
    __tablename__ = "student_attendances"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    stream_id = Column(Integer, ForeignKey("streams.id"), nullable=False)
    time = Column(DateTime, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # Relationships
    student = relationship("Student", back_populates="attendances")
    
    @declared_attr
    def session(cls):
        return relationship("Session", back_populates="student_attendances")
    
    def __repr__(self):
        return f"<StudentAttendance(id={self.id})>"