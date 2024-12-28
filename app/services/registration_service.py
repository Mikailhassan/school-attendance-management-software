from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, School
from app.schemas import (
    SchoolRegistrationRequest,
    SchoolAdminRegistrationRequest,
    TeacherRegistrationRequest,
    StudentRegistrationRequest,
    ParentRegistrationRequest
)
from app.core.security import get_password_hash
from app.core.logging import logger
from .base_service import BaseService

class RegistrationService(BaseService):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_school(self, request: SchoolRegistrationRequest) -> School:
        """Register a new school"""
        # Check if school with same name exists
        query = select(School).where(School.name == request.name)
        result = await self.db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School with this name already exists"
            )

        school = School(
            name=request.name,
            address=request.address,
            phone=request.phone,
            email=request.email,
            created_at=datetime.utcnow()
        )
        
        self.db.add(school)
        await self.db.commit()
        await self.db.refresh(school)
        
        logger.info(f"New school registered: {school.name}")
        return school

    async def register_school_admin(
        self,
        request: SchoolAdminRegistrationRequest
    ) -> User:
        """Register a school admin"""
        # Verify school exists using registration number
        query = select(School).where(
            School.registration_number == request.school_registration_number
        )
        result = await self.db.execute(query)
        school = result.scalar_one_or_none()
        
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"School with registration number {request.school_registration_number} not found"
            )
        
        # Check if admin already exists for school
        query = select(User).where(
            User.school_id == school.id,
            User.role == "school_admin"
        )
        result = await self.db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="School admin already exists for this school"
            )

        # Create admin user
        admin = User(
            name=request.name,
            email=request.email,
            phone=request.phone,  # Added phone from request
            password_hash=get_password_hash(request.password),
            role="school_admin",
            school_id=school.id,  # Use the found school's ID
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        
        logger.info(f"New school admin registered: {admin.email}")
        return admin

    async def register_teacher(
        self,
        request: TeacherRegistrationRequest,
        school_id: int,
        image: Optional[UploadFile] = None
    ) -> User:
        """Register a new teacher"""
        school = await self._get_school(school_id)
        
        # Check if teacher with same email exists
        query = select(User).where(User.email == request.email)
        result = await self.db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Handle image upload if provided
        image_path = None
        if image:
            image_path = await self._save_profile_image(image)

        teacher = User(
            name=request.name,
            email=request.email,
            password_hash=get_password_hash(request.password),
            role="teacher",
            school_id=school_id,
            profile_image=image_path,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.db.add(teacher)
        await self.db.commit()
        await self.db.refresh(teacher)
        
        logger.info(f"New teacher registered: {teacher.email}")
        return teacher

    async def get_school_users(
        self,
        school_id: int,
        role: Optional[str] = None
    ) -> List[User]:
        """Get all users for a specific school"""
        query = select(User).where(User.school_id == school_id)
        if role:
            query = query.where(User.role == role)
            
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_user(self, user_id: int) -> None:
        """Delete a user"""
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        await self.db.delete(user)
        await self.db.commit()
        logger.info(f"User deleted: {user.email}")

    async def _get_school(self, school_id: int) -> School:
        """Helper method to get and verify school exists"""
        query = select(School).where(School.id == school_id)
        result = await self.db.execute(query)
        school = result.scalar_one_or_none()
        
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found"
            )
            
        return school

    async def _save_profile_image(self, image: UploadFile) -> str:
        """Helper method to save profile image"""
        # Implementation for saving image to storage
        # This is a placeholder - implement actual file storage logic
        return f"/profile_images/{image.filename}"