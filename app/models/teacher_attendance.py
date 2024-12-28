from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, declared_attr
from .attendance_base import AttendanceBase

class TeacherAttendance(AttendanceBase):
    """
    Attendance record specific to teachers.
    """
    __tablename__ = "teacher_attendances"

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True)

    @declared_attr
    def teacher_id(cls):
        return Column(Integer, ForeignKey("teachers.id"), nullable=False)

    @declared_attr
    def session_id(cls): 
        return Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # Relationships
    @declared_attr
    def teacher(cls):
        return relationship("Teacher", back_populates="attendances", lazy="joined")

    @declared_attr
    def user(cls):
        return relationship("User", back_populates="teacher_attendances", lazy="joined")
    
    @declared_attr 
    def session(cls):
        return relationship("Session", back_populates="teacher_attendances", lazy="joined")

    def __repr__(self):
        return f"<TeacherAttendance(teacher_id={self.teacher_id})>"