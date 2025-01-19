from sqlalchemy import Column, Integer, DateTime, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func
from .base import TenantModel

class AttendanceBase(TenantModel):
    """
    Base attendance model for both student and teacher attendance.
    """
    __abstract__ = True

    @declared_attr
    def date(cls):
        return Column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def status(cls):
        return Column(String, nullable=False)



    @declared_attr
    def remarks(cls):
        return Column(String, nullable=True)

    @declared_attr
    def session_id(cls):
        return Column(Integer, ForeignKey('sessions.id'), nullable=True)

    @declared_attr
    def school_id(cls):
        return Column(Integer, ForeignKey('schools.id'), nullable=False)

    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id'), nullable=False)

    # Relationships
    @declared_attr
    def session(cls):
        return relationship("Session", back_populates=f"{cls.__name__.lower()}s")

    @declared_attr
    def school(cls):
        name = cls.__name__.lower()
        if name == 'teacherattendance':
            back_pop = 'teacher_attendance'
        elif name == 'studentattendance':
            back_pop = 'student_attendance'
        else:
            back_pop = f"{name}s"
        return relationship("School", back_populates=back_pop)

    @declared_attr
    def user(cls):
        name = cls.__name__.lower()
        if name == 'teacherattendance':
            back_pop = 'teacher_attendances'
        elif name == 'studentattendance':
            back_pop = 'student_attendances'
        else:
            back_pop = f"{name}s"
        return relationship("User", back_populates=back_pop)