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
        return Column(String, nullable=False)  # e.g., 'Present', 'Absent', 'Late'

    @declared_attr
    def check_in_time(cls):
        return Column(DateTime(timezone=True), nullable=True)

    @declared_attr
    def check_out_time(cls):
        return Column(DateTime(timezone=True), nullable=True)

    @declared_attr
    def is_approved(cls):
        return Column(Boolean, default=False)

    @declared_attr
    def remarks(cls):
        return Column(String, nullable=True)

    @declared_attr
    def session_id(cls):
        return Column(Integer, ForeignKey('sessions.id'), nullable=True)

    # Relationships
    @declared_attr
    def session(cls):
        return relationship("Session")

    @declared_attr
    def school(cls):
        return relationship("School", 
                          back_populates=f"{cls.__name__.lower()}_attendance")

    def __repr__(self):
        return f"<Attendance(date={self.date}, status={self.status})>"