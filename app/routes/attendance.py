from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.attendance_service import AttendanceService, AttendanceStatus
from app.models import User
from app.schemas import UserRole

router = APIRouter(tags=["Attendance"])

class TeacherAttendanceRequest(BaseModel):
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    period_id: Optional[int] = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    remarks: Optional[str] = None

class StudentAttendanceRequest(BaseModel):
    status: AttendanceStatus
    period_id: Optional[int] = None
    remarks: Optional[str] = None

class BulkStudentAttendanceRequest(BaseModel):
    stream_id: int
    session_id: int
    period_id: Optional[int] = None
    records: List[dict]  # List of {student_id: int, status: AttendanceStatus, remarks: Optional[str]}

@router.post("/teacher/{teacher_id}")
async def mark_teacher_attendance(
    teacher_id: int,
    attendance: TeacherAttendanceRequest,
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for a teacher with check-in/out times."""
    if current_user.role not in [UserRole.SCHOOL_ADMIN, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to mark teacher attendance"
        )
    
    # Only allow teachers to mark their own attendance
    if current_user.role == UserRole.TEACHER and current_user.id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers can only mark their own attendance"
        )

    service = AttendanceService(db)
    return await service.mark_teacher_attendance(
        teacher_id=teacher_id,
        school_id=current_user.school_id,
        session_id=session_id,
        check_in_time=attendance.check_in_time,
        check_out_time=attendance.check_out_time,
        period_id=attendance.period_id,
        status=attendance.status,
        remarks=attendance.remarks
    )

@router.post("/student/{student_id}")
async def mark_student_attendance(
    student_id: int,
    attendance: StudentAttendanceRequest,
    session_id: int,
    stream_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for a single student."""
    if current_user.role not in [UserRole.SCHOOL_ADMIN, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to mark student attendance"
        )

    service = AttendanceService(db)
    return await service.mark_student_attendance(
        student_id=student_id,
        school_id=current_user.school_id,
        session_id=session_id,
        stream_id=stream_id,
        status=attendance.status,
        period_id=attendance.period_id,
        remarks=attendance.remarks
    )
@router.post("/stream/{stream_id}/bulk")
async def mark_stream_attendance(
    stream_id: int,
    attendance: BulkStudentAttendanceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark attendance for all students in a stream."""
    if current_user.role not in [UserRole.SCHOOL_ADMIN, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to mark student attendance"
        )

    # Validate if the stream exists and belongs to the school
    stream = await validate_stream(db, stream_id, current_user.school_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found or not associated with your school"
        )

    # If period_id is provided, validate it exists and is valid for the session
    if attendance.period_id:
        period = await validate_period(db, attendance.period_id, attendance.session_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid period for the given session"
            )

    service = AttendanceService(db)
    results = []
    errors = []
    
    for record in attendance.records:
        try:
            result = await service.mark_student_attendance(
                student_id=record['student_id'],
                school_id=current_user.school_id,
                session_id=attendance.session_id,
                stream_id=stream_id,
                status=record['status'],
                period_id=attendance.period_id,
                remarks=record.get('remarks')
            )
            results.append({
                "student_id": record['student_id'],
                "status": "success",
                "details": result
            })
        except HTTPException as http_err:
            errors.append({
                "student_id": record['student_id'],
                "status": "error",
                "error_type": "validation_error",
                "details": http_err.detail
            })
        except Exception as e:
            errors.append({
                "student_id": record['student_id'],
                "status": "error",
                "error_type": "system_error",
                "details": str(e)
            })

    # Calculate summary statistics
    total_records = len(attendance.records)
    successful_records = len(results)
    failed_records = len(errors)

    return {
        "message": "Bulk attendance processing completed",
        "summary": {
            "total_records": total_records,
            "successful_records": successful_records,
            "failed_records": failed_records,
            "success_rate": f"{(successful_records/total_records)*100:.1f}%"
        },
        "results": results,
        "errors": errors if errors else None
    }

async def validate_stream(db: AsyncSession, stream_id: int, school_id: int):
    """Validate if stream exists and belongs to the school."""
    result = await db.execute(
        select(Stream).filter(
            Stream.id == stream_id,
            Stream.school_id == school_id
        )
    )
    return result.scalar_one_or_none()

async def validate_period(db: AsyncSession, period_id: int, session_id: int):
    """Validate if period exists and belongs to the session."""
    result = await db.execute(
        select(Period).filter(
            Period.id == period_id,
            Period.session_id == session_id
        )
    )
    return result.scalar_one_or_none()