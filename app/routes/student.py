from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from app.schemas.student import (
    StudentRegistrationRequest,
    StudentBaseResponse,
    StudentDetailResponse,
    StudentAttendanceSummary,
    StudentListResponse,
    StudentUpdateResponse
)
from app.services import RegistrationService
from app.models import User
from app.core.database import get_db
from app.core.dependencies import get_current_user, verify_school_access

router = APIRouter(tags=["Students"])

# Dependency to get registration service
def get_registration_service(db: AsyncSession = Depends(get_db)) -> RegistrationService:
    return RegistrationService(db)

@router.post("/", response_model=StudentBaseResponse, status_code=status.HTTP_201_CREATED)
async def register_student(
    request: StudentRegistrationRequest,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """
    Register a new student. Only accessible by school admins.
    """
    if not current_user.is_school_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school administrators can register students"
        )
    
    try:
        return await registration_service.register_student(
            request=request,
            school_id=current_user.school_id,
            created_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=StudentListResponse)
async def list_students(
    form: Optional[str] = Query(None, description="Filter by form/grade"),
    stream: Optional[str] = Query(None, description="Filter by stream/class"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """
    List all students in the school with pagination and filtering.
    Accessible by school admins and teachers.
    """
    if not (current_user.is_school_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        students, total_count = await registration_service.list_students(
            school_id=current_user.school_id,
            form=form,
            stream=stream,
            page=page,
            limit=limit
        )
        return StudentListResponse(
            students=students,
            total_count=total_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{student_id}", response_model=StudentDetailResponse)
async def get_student_details(
    student_id: int,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """
    Get detailed information about a specific student, including attendance summary.
    Accessible by school admins, teachers, and the student's parents.
    """
    try:
        # Check authorization and verify school access
        student = await registration_service.get_student(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Verify student belongs to the same school
        if student.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - Student belongs to a different school"
            )
        
        # Verify access permissions
        if not (current_user.is_school_admin or 
                current_user.is_teacher or 
                (current_user.is_parent and student.parent_id == current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get detailed student info including attendance
        return await registration_service.get_student_details(
            student_id=student_id,
            school_id=current_user.school_id
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{student_id}/attendance", response_model=StudentAttendanceSummary)
async def get_student_attendance(
    student_id: int,
    term: Optional[str] = Query(None, description="Filter by school term"),
    year: Optional[int] = Query(None, description="Filter by year"),
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """
    Get a student's attendance summary with optional term/year filtering.
    Accessible by school admins, teachers, and the student's parents.
    """
    try:
        # Check authorization and verify school access
        student = await registration_service.get_student(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Verify student belongs to the same school
        if student.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - Student belongs to a different school"
            )
        
        # Verify access permissions
        if not (current_user.is_school_admin or 
                current_user.is_teacher or 
                (current_user.is_parent and student.parent_id == current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return await registration_service.get_student_attendance_summary(
            student_id=student_id,
            school_id=current_user.school_id,
            term=term,
            year=year
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.patch("/{student_id}", response_model=StudentUpdateResponse)
async def update_student(
    student_id: int,
    update_data: StudentRegistrationRequest,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """
    Update student information. Only accessible by school admins.
    """
    if not current_user.is_school_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school administrators can update student information"
        )
    
    try:
        # Verify student belongs to the same school
        student = await registration_service.get_student(student_id)
        if not student or student.school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found in your school"
            )
            
        return await registration_service.update_student(
            student_id=student_id,
            update_data=update_data,
            school_id=current_user.school_id,
            updated_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )