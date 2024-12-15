from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

import logging
import enum

# Custom Exceptions
class AttendanceError(Exception):
    """Base exception for attendance-related errors."""
    pass

class AttendanceAlreadyMarkedError(AttendanceError):
    """Raised when attendance is already marked for the day."""
    pass

class InvalidCheckTypeError(AttendanceError):
    """Raised when an invalid check type is provided."""
    pass

class CheckType(str, enum.Enum):
    """Enumeration for check types."""
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"

class UserRole(str, enum.Enum):
    """Enumeration for user roles."""
    STUDENT = "student"
    TEACHER = "teacher"
    SCHOOL_ADMIN = "school_admin"

class AttendanceRepository:
    """Repository for handling database operations related to attendance."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_user_by_id(self, user_id: int) -> Any:
        """Retrieve a user by their ID."""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    async def get_today_attendance(self, user_id: int, school_id: int) -> Any:
        """Get today's attendance record for a user."""
        today = datetime.utcnow().date()
        result = await self.db.execute(
            select(Attendance)
            .filter(
                Attendance.user_id == user_id,
                Attendance.school_id == school_id,
                Attendance.check_in_time >= datetime.combine(today, datetime.min.time()),
                Attendance.check_in_time < datetime.combine(today + timedelta(days=1), datetime.min.time())
            )
        )
        return result.scalars().first()

    async def get_latest_attendance(self, user_id: int, school_id: int) -> Any:
        """Get the latest attendance record for a user."""
        result = await self.db.execute(
            select(Attendance)
            .filter(
                Attendance.user_id == user_id,
                Attendance.school_id == school_id
            )
            .order_by(Attendance.id.desc())
        )
        return result.scalars().first()

    async def get_attendance_records(self, start_date: date, end_date: date, school_id: int) -> List[Any]:
        """Retrieve attendance records within a specific date range."""
        result = await self.db.execute(
            select(Attendance)
            .filter(
                Attendance.school_id == school_id,
                Attendance.check_in_time >= datetime.combine(start_date, datetime.min.time()),
                Attendance.check_in_time <= datetime.combine(end_date, datetime.max.time())
            )
            .order_by(Attendance.check_in_time)
        )
        return result.scalars().all()

class AttendanceService:
    """Service for managing attendance operations."""
    
    def __init__(self, db_session: AsyncSession, fingerprint_service: Any):
        self.db = db_session
        self.repository = AttendanceRepository(db_session)
        self.fingerprint_service = fingerprint_service
        self.logger = logging.getLogger(self.__class__.__name__)

    async def mark_attendance(self, user_id: int, attendance_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Central method to mark attendance based on user role.
        
        Args:
            user_id (int): ID of the user marking attendance
            attendance_data (dict): Attendance marking details
        
        Returns:
            dict: Attendance marking result
        """
        try:
            user = await self.repository.get_user_by_id(user_id)
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            if user.role == UserRole.TEACHER:
                return await self.mark_teacher_attendance(
                    user_id, 
                    attendance_data.get('check_type', CheckType.CHECK_IN), 
                    user.school_id
                )
            elif user.role == UserRole.STUDENT:
                return await self.mark_student_attendance(user_id, True, user.school_id)
            else:
                raise HTTPException(status_code=400, detail="Invalid user role")

        except Exception as e:
            self.logger.error(f"Attendance marking failed: {str(e)}")
            raise

    async def mark_teacher_attendance(self, teacher_id: int, check_type: CheckType, school_id: int) -> Dict[str, str]:
        """
        Mark attendance for teachers with advanced checks.
        
        Args:
            teacher_id (int): ID of the teacher
            check_type (CheckType): Type of check (in/out)
            school_id (int): School identifier
        
        Returns:
            dict: Attendance marking result
        """
        try:
            fingerprint_template = await self.fingerprint_service.capture_fingerprint()

            async with self.db.begin():
                if check_type == CheckType.CHECK_IN:
                    await self._handle_teacher_check_in(teacher_id, fingerprint_template, school_id)
                elif check_type == CheckType.CHECK_OUT:
                    await self._handle_teacher_check_out(teacher_id, school_id)
                else:
                    raise InvalidCheckTypeError("Invalid check type")

            return {"message": f"Teacher {check_type} recorded successfully"}

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in teacher attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error occurred")

    async def mark_student_attendance(self, student_id: int, is_present: bool, school_id: int) -> Dict[str, str]:
        """
        Mark attendance for students.
        
        Args:
            student_id (int): ID of the student
            is_present (bool): Attendance status
            school_id (int): School identifier
        
        Returns:
            dict: Attendance marking result
        """
        try:
            existing_record = await self.repository.get_today_attendance(student_id, school_id)
            
            if existing_record:
                raise AttendanceAlreadyMarkedError("Attendance already recorded for today")

            async with self.db.begin():
                attendance_record = Attendance(
                    user_id=student_id,
                    check_in_time=datetime.utcnow(),
                    is_present=is_present,
                    school_id=school_id
                )
                self.db.add(attendance_record)

            return {"message": "Student attendance recorded successfully"}

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in student attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error occurred")

    async def generate_attendance_report(self, school_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Generate comprehensive attendance report.
        
        Args:
            school_id (int): School identifier
            start_date (date): Report start date
            end_date (date): Report end date
        
        Returns:
            list: Detailed attendance records
        """
        try:
            records = await self.repository.get_attendance_records(start_date, end_date, school_id)
            
            report = []
            for record in records:
                user = await self.repository.get_user_by_id(record.user_id)
                report.append({
                    "date": record.check_in_time.strftime("%Y-%m-%d"),
                    "user_id": record.user_id,
                    "name": user.name,
                    "role": user.role,
                    "check_in": record.check_in_time.strftime("%H:%M:%S"),
                    "check_out": record.check_out_time.strftime("%H:%M:%S") if record.check_out_time else "N/A",
                    "present": "Yes" if record.is_present else "No"
                })
            
            return report

        except Exception as e:
            self.logger.error(f"Attendance report generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate attendance report")

    async def _handle_teacher_check_in(self, teacher_id: int, fingerprint_template: str, school_id: int) -> None:
        """Internal method to handle teacher check-in."""
        latest_record = await self.repository.get_latest_attendance(teacher_id, school_id)
        
        if latest_record and latest_record.check_out_time is None:
            raise HTTPException(status_code=400, detail="Teacher already checked in")

        new_attendance = Attendance(
            user_id=teacher_id,
            check_in_time=datetime.utcnow(),
            fingerprint_template=fingerprint_template,
            is_present=True,
            school_id=school_id
        )
        self.db.add(new_attendance)

    async def _handle_teacher_check_out(self, teacher_id: int, school_id: int) -> None:
        """Internal method to handle teacher check-out."""
        latest_record = await self.repository.get_latest_attendance(teacher_id, school_id)
        
        if not latest_record or latest_record.check_out_time is not None:
            raise HTTPException(status_code=400, detail="Teacher has not checked in or already checked out")
        
        latest_record.check_out_time = datetime.utcnow()