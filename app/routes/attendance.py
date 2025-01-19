from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.core.dependencies import (
    get_current_user,
    verify_teacher,
    get_current_teacher,
    get_db,
    get_email_service,
    get_sms_service,
    get_current_school_admin
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
from app.schemas.attendance.responses import AttendanceResponse
from app.schemas.attendance.requests import AttendanceCreate
from app.schemas.attendance.info import AttendanceInfo
from app.schemas.attendance.info import ClassInfo, StreamInfo
from app.core.logging import logger
from app.schemas.school import SessionResponse
from app.models.user import User

router = APIRouter(prefix="/schools/{registration_number}", tags=["attendance"])

def get_attendance_service(
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
    sms_service: SMSService = Depends(get_sms_service)
) -> AttendanceService:
    return AttendanceService(db, email_service, sms_service)

@router.get("/sessions/active", response_model=SessionInfo)
async def get_active_session(
    registration_number: str,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_school_admin)
) -> SessionInfo:
    """
    Get active session for attendance marking.
    Returns the currently active session that applies to the current day and time.
    """
    try:
        clean_registration_number = registration_number.strip('{}')
        logger.debug(f"Processing request for school: {clean_registration_number}")
        
        # Get school using registration number
        school = await attendance_service.get_school_by_registration(clean_registration_number)
        if not school:
            raise HTTPException(
                status_code=404,
                detail="School not found"
            )
        
        # Check authorization
        if current_user.school_id != school.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this school's sessions"
            )
        
        # Get active session for current day and time
        session = await attendance_service.get_active_session(school.id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="No active session found for this school"
            )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in get_active_session")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/classes/{class_id}/students", response_model=List[StudentInfo])
async def get_class_students(
    registration_number: str,
    class_id: int,
    stream_id: Optional[int] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_school_admin)
):
    """Get all students in a class with their latest attendance status"""
    try:
        clean_registration_number = registration_number.strip('{}')
        school = attendance_service.get_school_by_registration(clean_registration_number)
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this school's data")
            
        return attendance_service.get_class_students_with_status(school.id, class_id, stream_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting class students")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/attendance/{student_id}", response_model=AttendanceInfo)
async def mark_student_attendance(
    student_id: int,
    attendance_data: AttendanceCreate,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_teacher)
):
    """Mark attendance for a student"""
    try:
        # Get active session first
        session = await attendance_service.get_active_session(current_user.school_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="No active session found"
            )
        
        # Get student with class and stream info
        student_info = await attendance_service.get_student_with_details(student_id)
        if not student_info:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )
            
        # Mark attendance with current user ID
        attendance = await attendance_service.mark_attendance(
            student_id=student_id,
            session_id=session.id,
            attendance_data=attendance_data,
            current_user_id=current_user.id
        )
        
        # Create response with all required fields
        return AttendanceInfo(
            student_id=student_id,
            class_id=int(student_info.class_id),  # Ensure it's an integer
            stream_id=int(student_info.stream_id),  # Ensure it's an integer
            session_id=session.id,
            school_id=current_user.school_id,
            date=attendance.date,
            class_name=student_info.class_name,
            stream_name=student_info.stream_name,
            status=attendance.status,
            check_in_time=attendance.check_in_time,
            check_out_time=attendance.check_out_time,
            remarks=attendance.remarks
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception("Type conversion error in mark_student_attendance")
        raise HTTPException(status_code=500, detail="Invalid ID format")
    except Exception as e:
        logger.exception("Unexpected error in mark_student_attendance")
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/sessions/{session_id}/streams/{stream_id}", response_model=List[AttendanceResponse])
# async def mark_stream_attendance(
#     registration_number: str,
#     session_id: int,
#     stream_id: int,
#     attendance_data: StreamAttendanceRequest,
#     attendance_service: AttendanceService = Depends(get_attendance_service),
#     current_user: User = Depends(get_current_school_admin)
# ):
#     """Mark attendance for all students in a stream"""
#     try:
#         clean_registration_number = registration_number.strip('{}')
#         school = attendance_service.get_school_by_registration(clean_registration_number)
        
#         if not school:
#             raise HTTPException(status_code=404, detail="School not found")
            
#         if current_user.school_id != school.id:
#             raise HTTPException(status_code=403, detail="Not authorized to mark attendance for this school")
        
#         attendance_data.school_id = school.id
#         attendance_data.session_id = session_id
#         attendance_data.stream_id = stream_id
        
#         return await attendance_service.mark_stream_attendance(attendance_data)
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception("Error marking stream attendance")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/sessions/{session_id}/classes/{class_id}", response_model=List[AttendanceResponse])
# async def mark_class_attendance(
#     registration_number: str,
#     session_id: int,
#     class_id: int,
#     attendance_data: BulkAttendanceRequest,
#     attendance_service: AttendanceService = Depends(get_attendance_service),
#     current_user: User = Depends(get_current_school_admin)
# ):
#     """Mark attendance for multiple streams in a class"""
#     try:
#         clean_registration_number = registration_number.strip('{}')
#         school = attendance_service.get_school_by_registration(clean_registration_number)
        
#         if not school:
#             raise HTTPException(status_code=404, detail="School not found")
            
#         if current_user.school_id != school.id:
#             raise HTTPException(status_code=403, detail="Not authorized to mark attendance for this school")
        
#         attendance_data.school_id = school.id
#         attendance_data.session_id = session_id
#         attendance_data.class_id = class_id
        
#         marked_attendance = []
#         for stream_id in attendance_data.stream_ids:
#             stream_data = StreamAttendanceRequest(
#                 stream_id=stream_id,
#                 class_id=class_id,
#                 session_id=session_id,
#                 school_id=school.id,
#                 attendance_data=[
#                     data for data in attendance_data.attendance_data 
#                     if data.stream_id == stream_id
#                 ]
#             )
#             stream_attendance = await attendance_service.mark_stream_attendance(stream_data)
#             marked_attendance.extend(stream_attendance)
        
#         return marked_attendance
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.exception("Error marking class attendance")
#         raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/attendance/classes",
    response_model=List[ClassInfo],
    responses={
        404: {"description": "School not found"},
        403: {"description": "Not authorized"},
    }
)
async def get_attendance_classes(
    registration_number: str,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_teacher)
):
    """Get all classes available for attendance marking"""
    try:
        school = await attendance_service.get_school_by_registration(registration_number)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        classes = await attendance_service.get_attendance_classes(school.id)
        return classes
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting attendance classes")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/attendance/classes/{class_id}/streams",
    response_model=List[StreamInfo],
    responses={
        404: {"description": "Class not found"},
        403: {"description": "Not authorized"},
    }
)
async def get_attendance_streams(
    registration_number: str,
    class_id: int,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_teacher)
):
    """Get all streams in a class for attendance marking"""
    try:
        school = await attendance_service.get_school_by_registration(registration_number)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        streams = await attendance_service.get_attendance_streams(school.id, class_id)
        return streams
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting attendance streams")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/attendance/classes/{class_id}/students",
    response_model=List[StudentInfo],
    responses={
        404: {"description": "Class not found"},
        403: {"description": "Not authorized"},
    }
)
async def get_attendance_students(
    registration_number: str,
    class_id: int,
    stream_id: Optional[int] = None,
    date: Optional[date] = Query(None),
    status: Optional[str] = Query(None, enum=["present", "absent", "late"]),
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_teacher)
):
    """
    Get students for attendance marking with filters:
    - Optional stream_id
    - Optional date
    - Optional attendance status
    """
    try:
        school = await attendance_service.get_school_by_registration(registration_number)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        students = await attendance_service.get_attendance_students(
            school_id=school.id,
            class_id=class_id,
            stream_id=stream_id,
            date=date,
            status=status
        )
        return students
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting attendance students")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/students/{student_id}/attendance", response_model=AttendanceResponse)
async def update_student_attendance(
    registration_number: str,
    student_id: int,
    attendance_data: AttendanceRequest,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_school_admin)
):
    """Update attendance for a specific student"""
    try:
        clean_registration_number = registration_number.strip('{}')
        school = attendance_service.get_school_by_registration(clean_registration_number)
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized to update attendance for this school")
        
        attendance_data.school_id = school.id
        
        return await attendance_service.update_student_attendance(
            student_id=student_id,
            attendance_data=attendance_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating student attendance")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/students/{student_id}/attendance", response_model=List[AttendanceResponse])
async def get_student_attendance_records(
    registration_number: str,
    student_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_school_admin)
):
    """Get attendance records for a specific student"""
    try:
        clean_registration_number = registration_number.strip('{}')
        school = attendance_service.get_school_by_registration(clean_registration_number)
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized to view attendance for this school")
        
        return attendance_service.get_student_attendance_records(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting student attendance records")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/streams/{stream_id}/attendance", response_model=List[AttendanceResponse])
async def get_stream_attendance_records(
    registration_number: str,
    stream_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_school_admin)
):
    """Get attendance records for an entire stream"""
    try:
        clean_registration_number = registration_number.strip('{}')
        school = attendance_service.get_school_by_registration(clean_registration_number)
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized to view attendance for this school")
        
        return attendance_service.get_stream_attendance_records(
            stream_id=stream_id,
            start_date=start_date,
            end_date=end_date
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting stream attendance records")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/classes/{class_id}/attendance/summary", response_model=dict)
async def get_class_attendance_summary(
    registration_number: str,
    class_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_school_admin)
):
    """Get attendance summary statistics for a class"""
    try:
        clean_registration_number = registration_number.strip('{}')
        school = attendance_service.get_school_by_registration(clean_registration_number)
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(status_code=403, detail="Not authorized to view attendance for this school")
        
        return attendance_service.get_class_attendance_summary(
            class_id=class_id,
            start_date=start_date,
            end_date=end_date
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting class attendance summary")
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/sessions", response_model=List[SessionResponse])
async def get_school_sessions(
    registration_number: str,
    attendance_service: AttendanceService = Depends(get_attendance_service),
    current_user: User = Depends(get_current_teacher)  # Teachers can view sessions
):
    """Get all active sessions defined for a school"""
    try:
        clean_registration_number = registration_number.strip('{}')
        school = await attendance_service.get_school_by_registration(clean_registration_number)
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(
                status_code=403, 
                detail="Not authorized to view sessions for this school"
            )
        
        sessions = await attendance_service.get_school_sessions(school.id)
        return sessions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting school sessions")
        raise HTTPException(status_code=500, detail=str(e))    