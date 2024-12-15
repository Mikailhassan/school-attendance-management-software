from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, Date, Enum, String, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from .base import TenantModel
import enum
import logging
import json
import uuid

class AttendanceStatus(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EARLY_DEPARTURE = "early_departure"
    EXCUSED = "excused"

class AttendanceAuditLog(TenantModel):
    """
    Detailed audit log for tracking attendance changes and actions
    """
    __tablename__ = "attendance_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # e.g., "create", "update", "validate"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, nullable=True)
    
    attendance = relationship("Attendance", back_populates="audit_logs")
    user = relationship("User")

class Attendance(TenantModel):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    
    date = Column(Date, nullable=False, default=datetime.utcnow().date)
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    
    status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.ABSENT)
    total_attendance_time = Column(Integer, nullable=True)
    
    # New fields for sophisticated scheduling
    scheduled_check_in = Column(DateTime, nullable=True)
    scheduled_check_out = Column(DateTime, nullable=True)
    is_weekend = Column(Boolean, default=False)
    is_holiday = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="attendances")
    school = relationship("School", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")
    audit_logs = relationship("AttendanceAuditLog", back_populates="attendance")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)

    def validate_attendance(self, current_user_id):
        """
        Advanced attendance validation with comprehensive checks
        
        :param current_user_id: ID of user performing the validation
        """
        try:
            # Time consistency checks
            self._validate_time_consistency()
            
            # Schedule-based validations
            self._validate_against_schedule()
            
            # Status determination
            self._determine_attendance_status()
            
            # Audit logging
            self._log_validation(current_user_id)
        
        except ValueError as e:
            self._log_validation_error(current_user_id, str(e))
            raise

    def _validate_time_consistency(self):
        """
        Comprehensive time validation
        """
        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                raise ValueError("Check-out time must be after check-in time.")
            
            # Calculate total attendance time
            attendance_duration = self.check_out_time - self.check_in_time
            self.total_attendance_time = int(attendance_duration.total_seconds() / 60)

    def _validate_against_schedule(self):
        """
        Advanced schedule-based validation
        
        Checks against:
        - Scheduled check-in/out times
        - Weekends
        - Holidays
        - Configured school-specific schedules
        """
        if not self.scheduled_check_in or not self.scheduled_check_out:
            # In a real system, fetch from school or class schedule
            raise ValueError("No scheduled times found for this attendance record.")
        
        # Weekend check
        if self.is_weekend:
            self.status = AttendanceStatus.EXCUSED
            return
        
        # Holiday check
        if self.is_holiday:
            self.status = AttendanceStatus.EXCUSED
            return
        
        # Detailed schedule comparison
        late_threshold = timedelta(minutes=15)
        early_departure_threshold = timedelta(minutes=30)
        
        if self.check_in_time and self.check_in_time > self.scheduled_check_in + late_threshold:
            self._logger.warning(f"Late arrival detected: {self.student_id}")

        if self.check_out_time and self.check_out_time < self.scheduled_check_out - early_departure_threshold:
            self._logger.warning(f"Early departure detected: {self.student_id}")

    def _determine_attendance_status(self):
        """
        Comprehensive status determination logic
        """
        if not self.check_in_time:
            self.status = AttendanceStatus.ABSENT
            return

        # Check against schedule status
        total_scheduled_time = self.scheduled_check_out - self.scheduled_check_in
        min_attendance_percentage = 0.7  # 70% of scheduled time

        if self.total_attendance_time:
            attendance_percentage = self.total_attendance_time / total_scheduled_time.total_seconds() * 60
            
            if attendance_percentage < min_attendance_percentage:
                self.status = AttendanceStatus.ABSENT
            elif self.is_weekend or self.is_holiday:
                self.status = AttendanceStatus.EXCUSED
            else:
                self.status = AttendanceStatus.PRESENT

    def _log_validation(self, user_id):
        """
        Create an audit log entry for successful validation
        
        :param user_id: ID of user performing the validation
        """
        audit_log = AttendanceAuditLog(
            attendance_id=self.id,
            action_type="validate",
            user_id=user_id,
            details={
                "status": self.status.value,
                "total_attendance_time": self.total_attendance_time,
                "check_in_time": self.check_in_time.isoformat() if self.check_in_time else None,
                "check_out_time": self.check_out_time.isoformat() if self.check_out_time else None
            }
        )
        # In a real system, you'd use the session to add this log
        # session.add(audit_log)

    def _log_validation_error(self, user_id, error_message):
        """
        Log validation errors
        
        :param user_id: ID of user performing the validation
        :param error_message: Specific error message
        """
        self._logger.error(f"Attendance validation error for student {self.student_id}: {error_message}")
        
        audit_log = AttendanceAuditLog(
            attendance_id=self.id,
            action_type="validation_error",
            user_id=user_id,
            details={
                "error_message": error_message,
                "student_id": self.student_id
            }
        )
       
        session.add(audit_log)

    @classmethod
    def create_attendance(cls, user_id, school_id, student_id, 
                           scheduled_check_in, scheduled_check_out, 
                           check_in_time=None, check_out_time=None,
                           is_weekend=False, is_holiday=False):
        """
        Advanced attendance creation method
        
        :param user_id: ID of user creating the record
        :param school_id: ID of the school
        :param student_id: ID of the student
        :param scheduled_check_in: Scheduled check-in time
        :param scheduled_check_out: Scheduled check-out time
        :param check_in_time: Actual check-in time
        :param check_out_time: Actual check-out time
        :param is_weekend: Flag for weekend attendance
        :param is_holiday: Flag for holiday attendance
        """
        attendance = cls(
            user_id=user_id,
            school_id=school_id,
            student_id=student_id,
            scheduled_check_in=scheduled_check_in,
            scheduled_check_out=scheduled_check_out,
            check_in_time=check_in_time or datetime.utcnow(),
            check_out_time=check_out_time,
            is_weekend=is_weekend,
            is_holiday=is_holiday
        )
        
        
        attendance.validate_attendance(user_id)
        return attendance