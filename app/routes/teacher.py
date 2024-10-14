from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.registration_service import RegistrationService
from app.models.user import User 
from app.dependencies import get_current_school_admin, get_current_super_admin, get_db
from app.schemas import TeacherRegistrationRequest, Teacher


router = APIRouter(tags=["teachers"])

@router.post("/register")
async def register_teacher_route(
    request: TeacherRegistrationRequest, 
    current_admin: User = Depends(get_current_school_admin),  # or get_current_super_admin
    db: Session = Depends(get_db)  # Ensure you have access to the database
):
    """
    Register a new teacher. Only accessible by school admins.
    """
    registration_service = RegistrationService(db)  # Create an instance of RegistrationService
    return await registration_service.register_teacher(request)

@router.get("/all")
async def list_all_teachers(
    current_admin: User = Depends(get_current_school_admin),  # or get_current_super_admin
    db: Session = Depends(get_db)
):
    """
    List all teachers in the school. Accessible by school admins.
    """
    registration_service = RegistrationService(db)  # Create an instance of RegistrationService
    return await registration_service.list_teachers(current_admin)

@router.get("/{teacher_id}")
async def get_teacher_details(
    teacher_id: int, 
    current_admin: User = Depends(get_current_school_admin),  # or get_current_super_admin
    db: Session = Depends(get_db)
):
    """
    Get the details of a specific teacher by ID, including attendance analysis 
    for the current week. Accessible by school admins.
    """
    registration_service = RegistrationService(db)  # Create an instance of RegistrationService

    # Fetch the teacher's profile
    teacher = await registration_service.get_teacher(teacher_id, current_admin)
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Fetch the teacher's attendance summary for the current week
    attendance_summary = await registration_service.get_teacher_attendance_summary(teacher_id, db)

    # Return the teacher profile with attendance analysis
    return {
        "teacher_info": teacher,
        "attendance_summary": attendance_summary
    }
