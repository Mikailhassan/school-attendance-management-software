# routes/student.py
from fastapi import APIRouter, Depends
from app.services.registration_service import register_student, list_students, get_student
from app.schemas import StudentRegisterRequest
from app.dependencies import get_current_school_admin

router = APIRouter()

@router.post("/register")
async def register_student_route(request: StudentRegisterRequest, current_admin: str = Depends(get_current_school_admin)):
    return await register_student(request, current_admin)

@router.get("/all")
async def list_all_students(current_admin: str = Depends(get_current_school_admin)):
    return await list_students()

@router.get("/{student_id}")
async def get_student_details(student_id: int, current_admin: str = Depends(get_current_school_admin)):
    return await get_student(student_id)
