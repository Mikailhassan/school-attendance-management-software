from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.dependencies import get_current_school_admin, get_db
from app.schemas import (
    TeacherRegistrationRequest,
    TeacherUpdateRequest,
    TeacherResponse,
    TeacherListResponse,
    TeacherDetailResponse
)
from app.services.teacher_service import TeacherService
from app.schemas.auth.requests import UserInDB
from app.core.logging import logging

router = APIRouter(
    prefix="/schools/{registration_number}/teachers",
    tags=["Teachers"],
    responses={
        404: {"description": "Not found"},
        403: {"description": "Forbidden"},
        401: {"description": "Unauthorized"}
    }
)

async def validate_registration_number(registration_number: str) -> str:
    """Validate and clean registration number"""
    if not registration_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration number is required"
        )
    return registration_number.strip('{}').upper()

@router.post(
    "",
    response_model=TeacherResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Teacher successfully registered"},
        400: {"description": "Invalid input"}
    }
)
async def register_teacher(
    registration_number: str = Path(..., description="School registration number"),
    teacher_data: TeacherRegistrationRequest = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Register a new teacher with default login credentials."""
    clean_reg_number = await validate_registration_number(registration_number)
    teacher_service = TeacherService(db)
    
    try:
        teacher = await teacher_service.register_teacher(
            clean_reg_number,
            teacher_data,
            background_tasks
        )
        await db.commit()
        return TeacherResponse.from_orm(teacher)
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "",
    response_model=List[TeacherListResponse],
    responses={
        200: {"description": "List of teachers retrieved successfully"}
    }
)
async def list_teachers(
    registration_number: str = Path(..., description="School registration number"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """List all teachers in a school."""
    clean_reg_number = await validate_registration_number(registration_number)
    teacher_service = TeacherService(db)
    
    try:
        teachers = await teacher_service.list_teachers(clean_reg_number)
        return [TeacherListResponse.from_orm(teacher) for teacher in teachers]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get(
    "/{teacher_id}",
    response_model=TeacherDetailResponse,
    responses={
        200: {"description": "Teacher details retrieved successfully"},
        404: {"description": "Teacher not found"}
    }
)
async def get_teacher_details(
    registration_number: str = Path(..., description="School registration number"),
    teacher_id: int = Path(..., ge=1, description="Teacher ID"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get detailed information about a specific teacher including attendance summary."""
    clean_reg_number = await validate_registration_number(registration_number)
    teacher_service = TeacherService(db)
    
    try:
        teacher = await teacher_service.get_teacher_details(
            clean_reg_number,
            teacher_id
        )
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher not found"
            )
        return TeacherDetailResponse.from_orm(teacher)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch(
    "/{teacher_id}",
    response_model=TeacherResponse
)
async def update_teacher(
    registration_number: str = Path(..., description="School registration number"),
    teacher_id: int = Path(..., ge=1, description="Teacher ID"),
    teacher_data: TeacherUpdateRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Update teacher information"""
    clean_reg_number = await validate_registration_number(registration_number)
    teacher_service = TeacherService(db)
    
    try:
        # Convert Pydantic model to dict, excluding unset values
        update_data = teacher_data.model_dump(exclude_unset=True)
        
        teacher = await teacher_service.update_teacher(
            clean_reg_number,
            teacher_id,
            update_data
        )
        await db.commit()
        return TeacherResponse.from_orm(teacher)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in update_teacher endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the teacher."
        )

@router.get(
    "/tsc/{tsc_number}",
    response_model=TeacherResponse,
    responses={
        200: {"description": "Teacher retrieved successfully"},
        404: {"description": "Teacher not found"}
    }
)
async def get_teacher_by_tsc(
    registration_number: str = Path(..., description="School registration number"),
    tsc_number: str = Path(..., min_length=5, max_length=20, description="TSC number"),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get teacher details by TSC number."""
    clean_reg_number = await validate_registration_number(registration_number)
    teacher_service = TeacherService(db)
    
    try:
        teacher = await teacher_service.get_teacher_by_tsc(
            clean_reg_number,
            tsc_number
        )
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Teacher with TSC number {tsc_number} not found"
            )
        return TeacherResponse.from_orm(teacher)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )