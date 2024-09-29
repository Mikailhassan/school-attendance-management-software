# routes/attendance.py
from fastapi import APIRouter, Depends
from app.services.attendance_service import mark_attendance, view_attendance_by_date
from app.schemas import AttendanceRequest
from app.utils.fingerprint import capture_fingerprint  # Handle fingerprint system
from app.dependencies import get_current_school_admin

router = APIRouter()

@router.post("/mark")
async def mark_attendance_route(request: AttendanceRequest, current_admin: str = Depends(get_current_school_admin)):
    # Capture the fingerprint to identify the user
    user_id, check_type = await capture_fingerprint()  # check_type: 'check_in' or 'check_out'
    return await mark_attendance(user_id, check_type)

@router.get("/view/{date}")
async def view_attendance_route(date: str, current_admin: str = Depends(get_current_school_admin)):
    return await view_attendance_by_date(date)
