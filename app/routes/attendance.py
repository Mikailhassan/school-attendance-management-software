from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.core.dependencies import (
    get_current_user,
    verify_teacher,
    get_db,
    get_email_service,
    get_sms_service
)
from app.services.attendance_service import AttendanceService
from app.services.email_service import EmailService
from app.services.sms_service import SMSService
from app.schemas.attendance import (
    AttendanceRequest,
    StreamAttendanceRequest,
    BulkAttendanceRequest,
    ClassInfo,
    StudentInfo,
    SessionInfo
)
from app.models.user import User

router = APIRouter(tags=["attendance"])

def get_attendance_service(
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    sms_service: SMSService = Depends(get_sms_service)
) -> AttendanceService:
    return AttendanceService(db, email_service, sms_service)

# Session Management Endpoints
@router.get("/sessions/active", response_model=SessionInfo)
async def get_active_session(
    class_id: int,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Get active session for attendance marking."""
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    session = attendance_service.get_active_session(class_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No active session found for this class"
        )
    return session

# Student List and Information Endpoints
@router.get("/class/{class_id}/students", response_model=List[StudentInfo])
async def get_class_students(
    class_id: int,
    stream_id: Optional[int] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Get all students in a class with their latest attendance status."""
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return attendance_service.get_class_students_with_status(class_id, stream_id)

# Single Student Attendance Marking
@router.post("/student/mark")
async def mark_student_attendance(
    attendance_data: AttendanceRequest,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Mark attendance for a single student."""
    verify_teacher(current_user, attendance_data.school_id)
    
    return await attendance_service.mark_student_attendance(
        attendance_data=attendance_data,
        student_id=attendance_data.student_id
    )

# Stream Attendance Marking
@router.post("/stream/mark")
async def mark_stream_attendance(
    attendance_data: StreamAttendanceRequest,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Mark attendance for all students in a stream."""
    verify_teacher(current_user, attendance_data.school_id)
    
    return await attendance_service.mark_stream_attendance(attendance_data)

# Class Attendance Marking
@router.post("/class/{class_id}/mark")
async def mark_class_attendance(
    class_id: int,
    attendance_data: BulkAttendanceRequest,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Mark attendance for multiple streams in a class."""
    verify_teacher(current_user, attendance_data.school_id)
    
    marked_attendance = []
    for stream_id in attendance_data.stream_ids:
        stream_data = StreamAttendanceRequest(
            stream_id=stream_id,
            class_id=class_id,
            session_id=attendance_data.session_id,
            school_id=attendance_data.school_id,
            attendance_data=[
                data for data in attendance_data.attendance_data 
                if data.stream_id == stream_id
            ]
        )
        stream_attendance = await attendance_service.mark_stream_attendance(stream_data)
        marked_attendance.extend(stream_attendance)
    
    return marked_attendance

# Attendance Modification
@router.put("/student/{student_id}/update")
async def update_student_attendance(
    student_id: int,
    attendance_data: AttendanceRequest,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Update attendance for a specific student."""
    verify_teacher(current_user, attendance_data.school_id)
    
    return await attendance_service.update_student_attendance(
        student_id=student_id,
        attendance_data=attendance_data
    )

# Attendance Records Retrieval
@router.get("/student/{student_id}/records")
async def get_student_attendance_records(
    student_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Get attendance records for a specific student."""
    student = attendance_service.get_student_info(student_id)
    verify_teacher(current_user, student.school_id)
    
    return attendance_service.get_student_attendance_records(
        student_id=student_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/stream/{stream_id}/records")
async def get_stream_attendance_records(
    stream_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Get attendance records for an entire stream."""
    stream = attendance_service.get_stream_info(stream_id)
    verify_teacher(current_user, stream.school_id)
    
    return attendance_service.get_stream_attendance_records(
        stream_id=stream_id,
        start_date=start_date,
        end_date=end_date
    )

# Attendance Statistics and Reports
@router.get("/class/{class_id}/summary")
async def get_class_attendance_summary(
    class_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_user)
):
    """Get attendance summary statistics for a class."""
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return attendance_service.get_class_attendance_summary(
        class_id=class_id,
        start_date=start_date,
        end_date=end_date
    )