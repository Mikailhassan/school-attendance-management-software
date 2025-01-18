from datetime import datetime, date, time
from typing import List, Optional, Dict
from sqlalchemy import and_, select
from sqlalchemy.orm import Session as AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select
from types import SimpleNamespace
from app.models import Student, Class, Stream 

from app.models import (
    Student, Session, School, StudentAttendance,
    Class, Stream
)
from app.schemas.attendance import (
    StudentInfo,
    StreamAttendanceRequest
)
from app.schemas.attendance.requests import AttendanceCreate
from app.schemas.attendance.info import AttendanceInfo
from app.services.email_service import EmailService
from app.services.sms_service import SMSService
from app.core.logging import logger

class AttendanceService:
    def __init__(
        self,
        db: AsyncSession,
        email_service: EmailService,
        sms_service: SMSService
    ):
        self.db = db
        self.email_service = email_service
        self.sms_service = sms_service
        
    

    async def get_school_by_registration(self, registration_number: str) -> School:
        result = await self.db.execute(
            select(School).where(School.registration_number == registration_number.strip('{}'))
        )
        school = result.scalar_one_or_none()
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        return school

    async def get_active_session(self, school_id: int) -> Optional[Session]:
        current_date = date.today()
        current_time = datetime.now().replace(microsecond=0).time()
        current_weekday = datetime.now().strftime("%A").upper()
        
        logger.debug(f"Searching for session at: Date={current_date}, Time={current_time}, Day={current_weekday}")
        
        # First, let's check all sessions without any filters to see what's available
        all_sessions = await self.db.execute(
            select(Session).where(Session.school_id == school_id)
        )
        all_sessions = all_sessions.scalars().all()
        logger.debug(f"Total sessions for school: {len(all_sessions)}")
        for s in all_sessions:
            logger.debug(
                f"Session {s.name}:\n"
                f"  ID: {s.id}\n"
                f"  Active: {s.is_active}\n"
                f"  Time: {s.start_time}-{s.end_time}\n"
                f"  Dates: {s.start_date}-{s.end_date}\n"
                f"  School ID: {s.school_id}"
            )
        
        # Now get potentially active sessions with individual condition checks
        base_query = select(Session).where(Session.school_id == school_id)
        
        active_check = await self.db.execute(
            base_query.where(Session.is_active == True)
        )
        active_sessions = active_check.scalars().all()
        logger.debug(f"Sessions after active check: {[s.name for s in active_sessions]}")
        
        date_check = await self.db.execute(
            base_query.where(and_(
                Session.start_date <= current_date,
                Session.end_date >= current_date
            ))
        )
        date_valid_sessions = date_check.scalars().all()
        logger.debug(f"Sessions after date check: {[s.name for s in date_valid_sessions]}")
        
        # Finally, get all sessions meeting all criteria
        result = await self.db.execute(
            select(Session).where(
                and_(
                    Session.school_id == school_id,
                    Session.is_active == True,
                    Session.start_date <= current_date,
                    Session.end_date >= current_date
                )
            )
        )
        
        sessions = result.scalars().all()
        logger.debug(f"Found {len(sessions)} potentially active sessions")
        
        # Find matching session in Python
        for session in sessions:
            time_match = self._is_time_in_session(current_time, session.start_time, session.end_time)
            day_match = current_weekday in session.weekdays
            
            logger.debug(
                f"Checking session {session.name} (ID: {session.id}):\n"
                f"  Time match: {time_match}\n"
                f"  Day match: {day_match}\n"
                f"  Current time: {current_time}, Session time: {session.start_time}-{session.end_time}\n"
                f"  Current day: {current_weekday}, Session days: {session.weekdays}\n"
                f"  Start date: {session.start_date}, End date: {session.end_date}"
            )
            
            if time_match and day_match:
                logger.debug(f"Found matching session: {session.name}")
                return session
        
        logger.debug("No matching active session found")
        return None

    def _is_time_in_session(self, current_time: time, start_time: time, end_time: time) -> bool:
        """Helper method to check if current time falls within session time, handling overnight sessions."""
        logger.debug(f"Checking time {current_time} against session {start_time}-{end_time}")
        
        if start_time <= end_time:
            # Normal session within same day
            result = start_time <= current_time <= end_time
        else:
            # Overnight session (e.g., 23:00-04:00)
            result = current_time >= start_time or current_time <= end_time
            
        logger.debug(f"Time check result: {result}")
        return result


    async def get_student_with_details(self, student_id: int):
        """Get student information including class and stream names"""
        query = (
            select(
                Student,
                Class.name.label('class_name'),
                Stream.name.label('stream_name')
            )
            .join(Class, Student.class_id == Class.id)
            .join(Stream, Student.stream_id == Stream.id)
            .where(Student.id == student_id)
        )
        
        result = await self.db.execute(query)
        row = result.first()
        if not row:
            return None
            
        # Create a StudentInfo object with all required fields
        student_info = SimpleNamespace(
            id=row.Student.id,
            class_id=int(row.Student.class_id),  # Ensure integer type
            stream_id=int(row.Student.stream_id),  # Ensure integer type
            class_name=row.class_name,
            stream_name=row.stream_name
        )
        
        return student_info
    
    
    async def get_student_with_details(self, student_id: int):
        """Get student information including class and stream names"""
        query = (
            select(
                Student,
                Class.name.label('class_name'),
                Stream.name.label('stream_name')
            )
            .join(Class, Student.class_id == Class.id)
            .join(Stream, Student.stream_id == Stream.id)
            .where(Student.id == student_id)
        )
        
        result = await self.db.execute(query)
        row = result.first()
        if not row:
            return None
            
        # Create a StudentInfo object with all required fields
        student_info = SimpleNamespace(
            id=row.Student.id,
            class_id=row.Student.class_id,
            stream_id=row.Student.stream_id,
            class_name=row.class_name,
            stream_name=row.stream_name
        )
        
        return student_info

    async def mark_attendance(
        self,
        student_id: int,
        session_id: int, 
        attendance_data: AttendanceCreate,
        current_user_id: int  # Added current_user_id parameter
    ) -> StudentAttendance:
        # First, verify this is an active session at the current time
        session = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = session.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
            
        current_date = date.today()
        current_time = datetime.now().replace(microsecond=0).time()
        current_weekday = datetime.now().strftime("%A").upper()
        
        time_match = self._is_time_in_session(current_time, session.start_time, session.end_time)
        logger.debug(
            f"Validating session {session.name}:\n"
            f"  Time match: {time_match}\n"
            f"  Day match: {current_weekday in session.weekdays}\n"
            f"  Date match: {session.start_date <= current_date <= session.end_date}\n"
            f"  Current time: {current_time}, Session time: {session.start_time}-{session.end_time}\n"
            f"  Current day: {current_weekday}, Session days: {session.weekdays}"
        )
        
        # Validate that this session is currently active
        if not (
            session.is_active and
            session.start_date <= current_date <= session.end_date and
            time_match and
            current_weekday in session.weekdays
        ):
            raise HTTPException(
                status_code=400,
                detail="Cannot mark attendance: Session is not currently active"
            )

        # Check if attendance already exists
        existing = await self.db.execute(
            select(StudentAttendance).where(
                and_(
                    StudentAttendance.student_id == student_id,
                    StudentAttendance.session_id == session_id,
                    StudentAttendance.date == current_date
                )
            )
        )
        
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Attendance already marked for this session"
            )

        new_attendance = StudentAttendance(
            student_id=student_id,
            session_id=session_id,
            school_id=session.school_id,
            user_id=current_user_id,  # Added user_id
            date=current_date,
            status=attendance_data.status,
            remarks=attendance_data.remarks,
            is_approved=False
        )
        
        self.db.add(new_attendance)
        await self.db.commit()
        await self.db.refresh(new_attendance)
        
        # Notify parents if student is absent
        if attendance_data.status.upper() == "ABSENT":
            await self._notify_parent_about_absence(student_id, new_attendance)
        
        return new_attendance
    
    async def get_school_sessions(self, school_id: int) -> List[Session]:
        """Get all sessions defined for a school"""
        result = await self.db.execute(
            select(Session).where(
                and_(
                    Session.school_id == school_id,
                    Session.is_active == True
                )
            ).order_by(Session.start_time)
        )
        return result.scalars().all()

    async def mark_stream_attendance(
        self,
        attendance_data: StreamAttendanceRequest
    ) -> List[StudentAttendance]:
        marked_attendance = []
        
        # Validate session is active
        session = await self.get_active_session(attendance_data.school_id)
        if not session:
            raise HTTPException(
                status_code=400,
                detail="No active session found"
            )

        for student_record in attendance_data.attendance_data:
            try:
                attendance = await self.mark_attendance(
                    student_id=student_record.student_id,
                    session_id=session.id,
                    attendance_data=AttendanceCreate(
                        status=student_record.status,
                        remarks=student_record.remarks
                    )
                )
                marked_attendance.append(attendance)
            except HTTPException as e:
                if e.status_code != 400:  # Skip if already marked
                    raise e
                
        return marked_attendance

    async def get_student_attendance_records(
        self,
        student_id: int,
        start_date: date,
        end_date: Optional[date] = None
    ) -> List[StudentAttendance]:
        query = select(StudentAttendance).where(
            and_(
                StudentAttendance.student_id == student_id,
                StudentAttendance.date >= start_date
            )
        )
        
        if end_date:
            query = query.where(StudentAttendance.date <= end_date)
            
        result = await self.db.execute(query)
        return result.scalars().all()

    async def _notify_parent_about_absence(
        self,
        student_id: int,
        attendance: StudentAttendance
    ):
        """Internal method to notify parents about student absence"""
        try:
            # Get student and parent info
            student_result = await self.db.execute(
                select(Student).where(Student.id == student_id)
            )
            student = student_result.scalar_one_or_none()
            
            if not student or not student.parent_id:
                return

            # Notification logic here
            if student.parent.phone_number:
                await self.sms_service.send_sms(
                    to_number=student.parent.phone_number,
                    message=f"Your child {student.first_name} was marked absent today."
                )
                
            if student.parent.email:
                await self.email_service.send_email(
                    to_email=student.parent.email,
                    subject="Student Absence Notification",
                    content=f"Your child {student.first_name} was marked absent today."
                )
        except Exception as e:
            logger.error(f"Failed to send absence notification: {str(e)}")
            # notification failure shouldn't block attendance marking