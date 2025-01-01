from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.core.dependencies import get_current_user, verify_teacher
from app.services.attendance_service import AttendanceService
from app.services.email_service import EmailService
from app.schemas.attendance import (
    AttendanceRequest,
    AttendanceAnalytics,
    ClassAttendanceResponse,
    StudentAttendanceRecord
)
from app.core.dependencies import get_db, get_email_service
from app.models.user import User

router = APIRouter(prefix="/attendance", tags=["attendance"])

# Class Navigation and Information Endpoints
@router.get("/teacher/classes")
async def get_teacher_classes(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all classes assigned to the teacher."""
    verify_teacher(current_user, school_id)
    attendance_service = AttendanceService(db, None)
    return attendance_service.get_teacher_classes(current_user.id, school_id)

@router.get("/class/{class_id}/students")
async def get_class_students(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all students in a specific class with their latest attendance status."""
    attendance_service = AttendanceService(db, None)
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return attendance_service.get_class_students_with_status(class_id)

# Attendance Marking Endpoints
@router.post("/class/{class_id}/mark")
async def mark_class_attendance(
    class_id: int,
    attendance_data: List[AttendanceRequest],
    session_id: int,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    current_user: User = Depends(get_current_user)
):
    """Mark attendance for an entire class."""
    attendance_service = AttendanceService(db, email_service)
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return await attendance_service.mark_class_attendance(
        class_id=class_id,
        session_id=session_id,
        attendance_data=attendance_data,
        teacher_id=current_user.id
    )

@router.put("/class/{class_id}/update/{date}")
async def update_class_attendance(
    class_id: int,
    date: date,
    attendance_updates: List[AttendanceRequest],
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    current_user: User = Depends(get_current_user)
):
    """Update attendance for a class on a specific date."""
    attendance_service = AttendanceService(db, email_service)
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return await attendance_service.update_class_attendance(
        class_id=class_id,
        date=date,
        attendance_updates=attendance_updates,
        teacher_id=current_user.id
    )

# Attendance Records Viewing Endpoints
@router.get("/class/{class_id}/records")
async def get_class_attendance_records(
    class_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get attendance records for an entire class."""
    attendance_service = AttendanceService(db, None)
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return attendance_service.get_class_attendance_records(
        class_id=class_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/class/{class_id}/student/{student_id}/records")
async def get_student_attendance_records(
    class_id: int,
    student_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get attendance records for a specific student in a class."""
    attendance_service = AttendanceService(db, None)
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return attendance_service.get_student_attendance_records(
        class_id=class_id,
        student_id=student_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/class/{class_id}/summary")
async def get_class_attendance_summary(
    class_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get attendance summary statistics for a class."""
    attendance_service = AttendanceService(db, None)
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return attendance_service.get_class_attendance_summary(
        class_id=class_id,
        start_date=start_date,
        end_date=end_date
    )

# Active Session Check
@router.get("/class/{class_id}/active-session")
async def get_active_session(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if there's an active session for attendance marking."""
    attendance_service = AttendanceService(db, None)
    class_info = attendance_service.get_class_info(class_id)
    verify_teacher(current_user, class_info.school_id)
    
    return attendance_service.get_active_session(class_id)