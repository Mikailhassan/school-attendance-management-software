# routes/teacher.py
from fastapi import APIRouter, Depends
from app.services.registration_service import register_teacher, list_teachers, get_teacher
from app.schemas import TeacherRegisterRequest
from app.dependencies import get_current_school_admin

router = APIRouter()

@router.post("/register")
async def register_teacher_route(request: TeacherRegisterRequest, current_admin: str = Depends(get_current_school_admin)):
    return await register_teacher(request, current_admin)

@router.get("/all")
async def list_all_teachers(current_admin: str = Depends(get_current_school_admin)):
    return await list_teachers()

@router.get("/{teacher_id}")
async def get_teacher_details(teacher_id: int, current_admin: str = Depends(get_current_school_admin)):
    return await get_teacher(teacher_id)
