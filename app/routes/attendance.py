# routes/attendance.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.attendance_service import AttendanceService
from app.schemas import AttendanceRequest
from app.utils.fingerprint import capture_fingerprint  # Handle fingerprint system
from app.dependencies import get_current_teacher, get_current_school_admin

router = APIRouter()

# Dependency to get the Attendance Service
attendance_service = AttendanceService()

@router.post("/teachers/mark")
async def mark_teacher_attendance_route(
    request: AttendanceRequest,
    current_teacher: str = Depends(get_current_teacher)
):
    # Capture the fingerprint to identify the teacher
    user_id, check_type = await capture_fingerprint()  # check_type: 'check_in' or 'check_out'
    return await attendance_service.mark_attendance(user_id, check_type, scanner_type="teacher")

@router.post("/students/mark")
async def mark_student_attendance_route(
    request: AttendanceRequest,
    current_teacher: str = Depends(get_current_teacher)
):
    # Assume the teacher's ID is already captured through authentication
    teacher_id = current_teacher.id

    # List of student IDs to mark as present
    student_ids = request.student_ids

    # Mark attendance for each student
    for student_id in student_ids:
        await attendance_service.mark_student_attendance(student_id, teacher_id)

    return {"message": "Student attendance marked successfully"}

@router.get("/view/{date}")
async def view_attendance_route(
    date: str, 
    current_admin: str = Depends(get_current_school_admin)
):
    return await attendance_service.view_attendance_by_date(date)
