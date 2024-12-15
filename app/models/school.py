from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Date, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class AttendanceType(enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"

class AttendancePeriod(enum.Enum):
    MORNING_FIRST = "morning_first"
    MORNING_SECOND = "morning_second"
    AFTERNOON_FIRST = "afternoon_first"
    AFTERNOON_SECOND = "afternoon_second"
    EVENING_FIRST = "evening_first"
    EVENING_SECOND = "evening_second"

class BaseAttendance(Base):
    """
    Base abstract class for attendance tracking
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, default=lambda: datetime.utcnow().date())
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)
    type = Column(Enum(AttendanceType), nullable=False)
    period = Column(Enum(AttendancePeriod), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': None,
        'polymorphic_on': type
    }
    
    # Relationships
    user = relationship("User", back_populates="attendances")
    school = relationship("School", back_populates="attendances")
    
    def __repr__(self):
        return f"<Attendance(id={self.id}, user_id={self.user_id}, date={self.date}, type={self.type}, period={self.period})>"

class StudentAttendance(BaseAttendance):
    """
    Specific attendance model for students
    Supports multiple attendance entries per day
    """
    __tablename__ = 'student_attendance'
    
    __mapper_args__ = {
        'polymorphic_identity': AttendanceType.STUDENT
    }
    
    is_present = Column(Boolean, default=False, nullable=False)
    reason_for_absence = Column(String(255), nullable=True)
    additional_notes = Column(Text, nullable=True)
    
    def validate(self):
        """
        Validate student attendance record
        """
        if not self.is_present and not self.reason_for_absence:
            raise ValueError(f"Reason for absence must be provided when student is marked absent for {self.period.value} period")
        return True

class TeacherAttendance(BaseAttendance):
    """
    Specific attendance model for teachers
    """
    __tablename__ = 'teacher_attendance'
    
    __mapper_args__ = {
        'polymorphic_identity': AttendanceType.TEACHER
    }
    
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    
    @property
    def total_working_hours(self):
        """
        Calculate total working hours in minutes
        """
        if self.check_in_time and self.check_out_time:
            return int((self.check_out_time - self.check_in_time).total_seconds() / 60)
        return None
    
    def validate(self):
        """
        Validate teacher attendance record
        """
        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                raise ValueError(f"Check-out time must be after check-in time for {self.period.value} period")
        return True