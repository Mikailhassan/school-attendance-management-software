from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, declared_attr
from .attendance_base import AttendanceBase

class StudentAttendance(AttendanceBase):
    """
    Attendance record specific to students.
    """
    __tablename__ = "student_attendances"

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True)

    @declared_attr
    def student_id(cls):
        return Column(Integer, ForeignKey("students.id"), nullable=False)


    # Relationships
    @declared_attr
    def student(cls):
        return relationship("Student", back_populates="attendances", lazy="joined")

    @declared_attr
    def user(cls):
        return relationship("User", back_populates="student_attendances", lazy="joined")

    @declared_attr
    def session(cls):  # Added session relationship
        return relationship("Session", back_populates="student_attendances", lazy="joined")

    def __repr__(self):
        return f"<StudentAttendance(student_id={self.student_id})>"