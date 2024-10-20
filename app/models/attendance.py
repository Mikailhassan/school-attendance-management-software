from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import TenantModel

class Attendance(TenantModel):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("student.id"), nullable=False)  # Corrected table name
    date = Column(Date, nullable=False, default=datetime.utcnow().date)
    check_in_time = Column(DateTime, default=datetime.utcnow, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    is_present = Column(Boolean, default=False)

    user = relationship("User", back_populates="attendances")
    school = relationship("School", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance(user_id={self.user_id}, date={self.date}, present={self.is_present}, school_id={self.school_id}, student_id={self.student_id})>"

    def validate_attendance(self):
        if self.check_out_time and self.check_out_time < self.check_in_time:
            raise ValueError("Check-out time must be after check-in time.")
        if not self.user_id:
            raise ValueError("User ID must be provided.")
        if not self.school_id:
            raise ValueError("School ID must be provided.")
        if not self.student_id:
            raise ValueError("Student ID must be provided.")