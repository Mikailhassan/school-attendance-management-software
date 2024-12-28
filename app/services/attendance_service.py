from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
import logging
from enum import Enum

class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    SCHOOL_ADMIN = "school_admin"
    SUPER_ADMIN = "super_admin"

class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)

    async def mark_teacher_attendance(
        self,
        teacher_id: int,
        school_id: int,
        session_id: int,
        check_in_time: datetime,
        check_out_time: Optional[datetime] = None,
        period_id: Optional[int] = None,
        status: AttendanceStatus = AttendanceStatus.PRESENT,
        remarks: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark attendance for teachers with check-in and optional check-out times."""
        try:
            # Validate teacher exists and belongs to school
            teacher = await self._get_user(teacher_id, school_id, UserRole.TEACHER)
            if not teacher:
                raise HTTPException(status_code=404, detail="Teacher not found")

            # If period is specified, validate it exists and is current
            if period_id:
                period = await self._get_period(period_id, session_id)
                if not period:
                    raise HTTPException(status_code=404, detail="Invalid period")
                
                # Validate check-in time falls within period
                if not period.is_time_within_period(check_in_time):
                    raise HTTPException(
                        status_code=400, 
                        detail="Check-in time does not fall within specified period"
                    )

            # Check if attendance already exists for the period/day
            existing = await self._get_teacher_attendance(
                teacher_id, 
                school_id,
                check_in_time.date(),
                period_id
            )
            
            if existing:
                # Update check-out time if this is a check-out request
                if check_out_time:
                    existing.check_out_time = check_out_time
                    existing.remarks = remarks
                    await self.db.commit()
                    return {
                        "message": "Check-out time recorded successfully",
                        "attendance_id": existing.id
                    }
                raise HTTPException(
                    status_code=400, 
                    detail="Attendance already marked for this period/date"
                )

            # Create new attendance record
            new_attendance = TeacherAttendance(
                user_id=teacher_id,
                school_id=school_id,
                session_id=session_id,
                period_id=period_id,
                check_in_time=check_in_time,
                check_out_time=check_out_time,
                status=status,
                remarks=remarks,
                date=check_in_time.date()
            )
            self.db.add(new_attendance)
            await self.db.commit()
            
            return {
                "message": "Teacher attendance recorded successfully",
                "attendance_id": new_attendance.id
            }

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in teacher attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to record attendance")

    async def mark_student_attendance(
        self,
        student_id: int,
        school_id: int,
        session_id: int,
        stream_id: int,
        status: AttendanceStatus,
        period_id: Optional[int] = None,
        remarks: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mark attendance for students with present/absent/late status."""
        try:
            # Validate student exists and belongs to school/stream
            student = await self._get_student(student_id, school_id, stream_id)
            if not student:
                raise HTTPException(
                    status_code=404, 
                    detail="Student not found in specified stream"
                )

            # If period specified, validate it exists
            if period_id:
                period = await self._get_period(period_id, session_id)
                if not period:
                    raise HTTPException(status_code=404, detail="Invalid period")

            current_date = datetime.now().date()

            # Check if attendance already exists
            existing = await self._get_student_attendance(
                student_id, 
                school_id,
                current_date,
                period_id
            )
            
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail="Attendance already marked for this period/date"
                )

            # Create new attendance record
            new_attendance = StudentAttendance(
                user_id=student_id,
                school_id=school_id,
                session_id=session_id,
                stream_id=stream_id,
                period_id=period_id,
                status=status,
                date=current_date,
                remarks=remarks
            )
            self.db.add(new_attendance)
            await self.db.commit()
            
            return {
                "message": "Student attendance recorded successfully",
                "attendance_id": new_attendance.id
            }

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in student attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to record attendance")

    async def get_attendance_summary(
        self,
        school_id: int,
        session_id: int,
        stream_id: Optional[int] = None,
        period_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get attendance summary for a school/stream within a date range."""
        try:
            # Default to current session dates if not specified
            if not start_date or not end_date:
                session = await self._get_session(session_id)
                start_date = session.start_date
                end_date = session.end_date

            # Build query based on parameters
            student_query = select(StudentAttendance).filter(
                StudentAttendance.school_id == school_id,
                StudentAttendance.session_id == session_id,
                StudentAttendance.date >= start_date,
                StudentAttendance.date <= end_date
            )
            
            teacher_query = select(TeacherAttendance).filter(
                TeacherAttendance.school_id == school_id,
                TeacherAttendance.session_id == session_id,
                TeacherAttendance.date >= start_date,
                TeacherAttendance.date <= end_date
            )

            if stream_id:
                student_query = student_query.filter(StudentAttendance.stream_id == stream_id)
            
            if period_id:
                student_query = student_query.filter(StudentAttendance.period_id == period_id)
                teacher_query = teacher_query.filter(TeacherAttendance.period_id == period_id)

            # Execute queries
            student_results = await self.db.execute(student_query)
            teacher_results = await self.db.execute(teacher_query)
            
            student_records = student_results.scalars().all()
            teacher_records = teacher_results.scalars().all()

            # Calculate statistics
            summary = {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "period_id": period_id
                },
                "students": {
                    "total": len(set(record.user_id for record in student_records)),
                    "present": len([r for r in student_records if r.status == AttendanceStatus.PRESENT]),
                    "absent": len([r for r in student_records if r.status == AttendanceStatus.ABSENT]),
                    "late": len([r for r in student_records if r.status == AttendanceStatus.LATE])
                },
                "teachers": {
                    "total": len(set(record.user_id for record in teacher_records)),
                    "present": len([r for r in teacher_records if r.status == AttendanceStatus.PRESENT]),
                    "late": len([r for r in teacher_records if r.status == AttendanceStatus.LATE])
                }
            }

            return summary

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in attendance summary: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate summary")

    # Helper methods
    async def _get_period(self, period_id: int, session_id: int):
        result = await self.db.execute(
            select(Period).filter(
                Period.id == period_id,
                Period.session_id == session_id
            )
        )
        return result.scalar_one_or_none()

    async def _get_user(self, user_id: int, school_id: int, role: UserRole):
        result = await self.db.execute(
            select(User).filter(
                User.id == user_id,
                User.school_id == school_id,
                User.role == role
            )
        )
        return result.scalar_one_or_none()

    async def _get_student(self, student_id: int, school_id: int, stream_id: int):
        result = await self.db.execute(
            select(User).join(StudentStream).filter(
                User.id == student_id,
                User.school_id == school_id,
                StudentStream.stream_id == stream_id,
                User.role == UserRole.STUDENT
            )
        )
        return result.scalar_one_or_none()

    async def _get_session(self, session_id: int):
        result = await self.db.execute(
            select(Session).filter(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def _get_teacher_attendance(
        self, 
        teacher_id: int, 
        school_id: int, 
        date: date,
        period_id: Optional[int] = None
    ):
        query = select(TeacherAttendance).filter(
            TeacherAttendance.user_id == teacher_id,
            TeacherAttendance.school_id == school_id,
            TeacherAttendance.date == date
        )
        
        if period_id:
            query = query.filter(TeacherAttendance.period_id == period_id)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_student_attendance(
        self, 
        student_id: int, 
        school_id: int, 
        date: date,
        period_id: Optional[int] = None
    ):
        query = select(StudentAttendance).filter(
            StudentAttendance.user_id == student_id,
            StudentAttendance.school_id == school_id,
            StudentAttendance.date == date
        )
        
        if period_id:
            query = query.filter(StudentAttendance.period_id == period_id)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()