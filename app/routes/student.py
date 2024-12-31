from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from sqlalchemy import select

from app.schemas.student import (
    StudentRegistrationRequest,
    StudentBaseResponse,
    StudentDetailResponse,
    StudentAttendanceSummary,
    StudentListResponse,
    StudentUpdateResponse,
    StudentUpdate
)
from app.services import RegistrationService
from app.models import User, Class, Stream
from app.core.database import get_db
from app.core.dependencies import get_current_user, verify_school_access

router = APIRouter(prefix="/api/v1/students", tags=["Students"])

def get_registration_service(db: AsyncSession = Depends(get_db)) -> RegistrationService:
    return RegistrationService(db)

async def verify_class_stream(
    db: AsyncSession,
    class_id: int,
    stream_id: Optional[int] = None,
    school_id: int = None
):
    """Verify that the class and stream exist and belong to the same school"""
    class_query = await db.execute(
        select(Class).where(Class.id == class_id, Class.school_id == school_id)
    )
    class_obj = class_query.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found or does not belong to your school"
        )
    
    if stream_id:
        stream_query = await db.execute(
            select(Stream).where(
                Stream.id == stream_id,
                Stream.class_id == class_id,
                Stream.school_id == school_id
            )
        )
        stream = stream_query.scalar_one_or_none()
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found or does not belong to the specified class"
            )
    
    return class_obj

@router.get("/me", response_model=StudentDetailResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """Get the current student's profile"""
    if not current_user.is_student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this endpoint"
        )
    
    return await registration_service.get_student_details(
        student_id=current_user.student.id,
        school_id=current_user.school_id
    )

@router.get("/me/attendance", response_model=StudentAttendanceSummary)
async def get_my_attendance(
    term: Optional[str] = Query(None, description="Filter by school term"),
    year: Optional[int] = Query(None, description="Filter by year"),
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """Get the current student's attendance summary"""
    if not current_user.is_student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this endpoint"
        )
    
    return await registration_service.get_student_attendance_summary(
        student_id=current_user.student.id,
        school_id=current_user.school_id,
        term=term,
        year=year
    )

@router.get("", response_model=StudentListResponse)
async def list_students(
    class_id: Optional[int] = Query(None, description="Filter by class"),
    stream_id: Optional[int] = Query(None, description="Filter by stream"),
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
            class_id=class_id,
            stream_id=stream_id,
            page=page,
            limit=limit
        )
        return StudentListResponse(
            students=students,
            total_count=total_count,
            page=page,
            limit=limit
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
    Get detailed information about a specific student.
    Accessible by school admins, teachers, and the student's parents.
    """
    student = await registration_service.get_student(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    if student.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student belongs to a different school"
        )
    
    if not (current_user.is_school_admin or 
            current_user.is_teacher or 
            (current_user.is_parent and student.parent_id == current_user.id) or
            (current_user.is_student and current_user.student.id == student_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return await registration_service.get_student_details(
        student_id=student_id,
        school_id=current_user.school_id
    )

@router.patch("/{student_id}", response_model=StudentUpdateResponse)
async def update_student(
    student_id: int,
    update_data: StudentUpdate,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service),
    db: AsyncSession = Depends(get_db)
):
    """Update student information. Only accessible by school admins."""
    if not current_user.is_school_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only school administrators can update student information"
        )
    
    student = await registration_service.get_student(student_id)
    if not student or student.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in your school"
        )
    
    if update_data.class_id or update_data.stream_id:
        await verify_class_stream(
            db=db,
            class_id=update_data.class_id or student.class_id,
            stream_id=update_data.stream_id,
            school_id=current_user.school_id
        )
    
    try:
        updated_student = await registration_service.update_student(
            student_id=student_id,
            update_data=update_data,
            school_id=current_user.school_id,
            updated_by=current_user.id
        )
        return StudentUpdateResponse(
            student=updated_student,
            message="Student information updated successfully"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )