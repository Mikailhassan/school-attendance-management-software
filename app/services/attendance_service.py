from datetime import datetime, time, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from fastapi import HTTPException

from app.models import (
    StudentAttendance, 
    TeacherAttendance,
    Session as SessionModel,
    Student,
    Class,
    Stream,
    Parent
)
from app.schemas.attendance import (
    AttendanceRequest,
    AttendanceAnalytics,
    StreamAttendanceRequest,
    ClassInfo,
    StudentInfo
)
from app.services.email_service import EmailService
from app.services.sms_service import SMSService

class AttendanceService:
    def __init__(
        self, 
        db: Session, 
        email_service: EmailService,
        sms_service: SMSService
    ):
        self.db = db
        self.email_service = email_service
        self.sms_service = sms_service

    def get_class_info(self, class_id: int) -> ClassInfo:
        """Get class information including streams."""
        class_data = self.db.query(Class).filter(Class.id == class_id).first()
        if not class_data:
            raise HTTPException(status_code=404, detail="Class not found")
        return class_data

    def get_active_session(self, class_id: int) -> Optional[SessionModel]:
        """Get current active session for a class."""
        now = datetime.now()
        session = self.db.query(SessionModel).filter(
            and_(
                SessionModel.class_id == class_id,
                SessionModel.start_time <= now,
                SessionModel.end_time >= now,
                SessionModel.status == 'Active'
            )
        ).first()
        return session

    def get_class_students_with_status(self, class_id: int) -> List[StudentInfo]:
        """Get all students in a class with their latest attendance status."""
        students = self.db.query(Student).filter(
            Student.class_id == class_id
        ).all()
        
        # Get latest attendance for each student
        student_info = []
        for student in students:
            latest_attendance = self.db.query(StudentAttendance).filter(
                StudentAttendance.student_id == student.id
            ).order_by(StudentAttendance.date.desc()).first()
            
            student_info.append(StudentInfo(
                id=student.id,
                name=f"{student.first_name} {student.last_name}",
                admission_number=student.admission_number,
                class_id=student.class_id,
                stream_id=student.stream_id,
                class_name=student.class_name,
                stream_name=student.stream_name,
                latest_attendance_status=latest_attendance.status if latest_attendance else None,
                last_attendance_date=latest_attendance.date if latest_attendance else None
            ))
        
        return student_info

    async def mark_student_attendance(
        self,
        attendance_data: AttendanceRequest,
        student_id: int
    ) -> StudentAttendance:
        """Mark attendance for a single student."""
        
        # Verify session exists and is active
        session = self.db.query(SessionModel).filter(
            and_(
                SessionModel.id == attendance_data.session_id,
                SessionModel.status == 'Active',
                or_(
                    SessionModel.class_id == attendance_data.class_id,
                    SessionModel.school_id == attendance_data.school_id
                )
            )
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=404, 
                detail="No active session found for this class"
            )

        # Check if attendance already marked for this session
        existing_attendance = self.db.query(StudentAttendance).filter(
            and_(
                StudentAttendance.student_id == student_id,
                StudentAttendance.session_id == session.id,
                StudentAttendance.date == datetime.now().date()
            )
        ).first()
        
        if existing_attendance:
            raise HTTPException(
                status_code=400,
                detail="Attendance already marked for this student in current session"
            )

        # Create attendance record
        attendance = StudentAttendance(
            student_id=student_id,
            school_id=attendance_data.school_id,
            class_id=attendance_data.class_id,
            stream_id=attendance_data.stream_id,
            session_id=session.id,
            status=attendance_data.status,
            check_in_time=attendance_data.check_in_time,
            check_out_time=attendance_data.check_out_time,
            remarks=attendance_data.remarks,
            date=datetime.now().date()
        )

        try:
            self.db.add(attendance)
            self.db.commit()
            self.db.refresh(attendance)

            # If student is absent, notify parent
            if attendance.status == 'absent':
                await self._notify_parent_about_absence(student_id, attendance)

            return attendance

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    async def mark_stream_attendance(
        self,
        attendance_data: StreamAttendanceRequest
    ) -> List[StudentAttendance]:
        """Mark attendance for all students in a stream."""
        marked_attendance = []
        
        for student_attendance in attendance_data.attendance_data:
            try:
                attendance = await self.mark_student_attendance(
                    student_attendance,
                    student_attendance.student_id
                )
                marked_attendance.append(attendance)
            except HTTPException as e:
                if e.status_code != 400:  # Skip if already marked
                    raise e
                
        return marked_attendance

    async def _notify_parent_about_absence(
        self,
        student_id: int,
        attendance: StudentAttendance
    ):
        """Send SMS and email notifications to parent about student absence."""
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return
            
        parent = self.db.query(Parent).filter(Parent.id == student.parent_id).first()
        if not parent:
            return

        # Send SMS if phone number available
        if parent.phone_number:
            message = (
                f"Dear Parent, your child {student.first_name} {student.last_name} "
                f"was marked absent for today's session on "
                f"{attendance.date.strftime('%Y-%m-%d')}. "
                f"Please contact the school for any clarification."
            )
            
            try:
                await self.sms_service.send_sms(
                    to_number=parent.phone_number,
                    message=message
                )
            except Exception as e:
                # Log error but don't stop execution
                print(f"Failed to send SMS: {str(e)}")

        # Send email if email available
        if parent.email:
            subject = f"Absence Notification - {student.first_name} {student.last_name}"
            content = f"""
            Dear Parent/Guardian,

            This is to inform you that {student.first_name} {student.last_name} 
            was marked absent for today's session ({attendance.date.strftime('%Y-%m-%d')}).

            If you believe this is an error, please contact the school administration.

            Best regards,
            School Administration
            """
            
            try:
                await self.email_service.send_email(
                    to_email=parent.email,
                    subject=subject,
                    content=content
                )
            except Exception as e:
                # Log error but don't stop execution
                print(f"Failed to send email: {str(e)}")