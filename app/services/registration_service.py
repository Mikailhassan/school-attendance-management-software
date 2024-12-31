from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.student import StudentUpdate
from sqlalchemy.orm import Session,joinedload

from app.models import User, School, Student,Parent
from app.schemas import (
    SchoolRegistrationRequest,
    SchoolAdminRegistrationRequest,
    TeacherRegistrationRequest,
    StudentRegistrationRequest,
    ParentRegistrationRequest,
    ParentCreate,
    ParentUpdate
    
)
from app.core.security import get_password_hash,generate_temporary_password
from app.core.logging import logger
from .base_service import BaseService
from app.utils.email_utils import send_email
from app.core.logging import logging

logger = logging.getLogger(__name__)

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
    

async def register_student(
    self,
    request: StudentRegistrationRequest,
    school_id: int,
    created_by: int
) -> Student:
    """Register a new student"""
    # Check if student with same admission number exists in the school
    query = select(Student).where(
        Student.admission_number == request.admission_number,
        Student.school_id == school_id
    )
    result = await self.db.execute(query)
    if result.scalar_one_or_none():
        raise ValueError("Student with this admission number already exists")

    # Create user account for student
    user = User(
        name=request.name,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role="student",
        school_id=school_id,
        created_by=created_by,
        created_at=datetime.utcnow()
    )
    self.db.add(user)
    await self.db.flush()  # To get the user.id

    # Create student record
    student = Student(
        name=request.name,
        admission_number=request.admission_number,
        date_of_birth=request.date_of_birth,
        class_id=request.class_id,
        stream_id=request.stream_id,
        user_id=user.id,
        parent_id=request.parent_id,
        school_id=school_id,
        created_by=created_by
    )
    
    self.db.add(student)
    await self.db.commit()
    await self.db.refresh(student)
    
    logger.info(f"New student registered: {student.name} ({student.admission_number})")
    return student

async def list_students(
    self,
    school_id: int,
    class_id: Optional[int] = None,
    stream_id: Optional[int] = None,
    page: int = 1,
    limit: int = 50
) -> tuple[List[Student], int]:
    """List students with filtering and pagination"""
    query = select(Student).where(Student.school_id == school_id)
    
    if class_id:
        query = query.where(Student.class_id == class_id)
    if stream_id:
        query = query.where(Student.stream_id == stream_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await self.db.scalar(count_query)

    # Add pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await self.db.execute(query)
    students = result.scalars().all()
    
    return students, total_count

async def update_student(
    self,
    student_id: int,
    update_data: StudentUpdate,
    school_id: int,
    updated_by: int
) -> Student:
    """Update student information"""
    student = await self.get_student(student_id)
    if not student:
        raise ValueError("Student not found")

    if student.school_id != school_id:
        raise ValueError("Student does not belong to your school")

    # Update student fields
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(student, field, value)

    student.updated_by = updated_by
    student.updated_at = datetime.utcnow()

    await self.db.commit()
    await self.db.refresh(student)
    
    logger.info(f"Student updated: {student.name} ({student.admission_number})")
    return student

class ParentRegistrationService:
    def __init__(self, db: Session):
        self.db = db

    async def create_parent_account(self, parent_data: ParentCreate) -> Parent:
        """Create a new parent account if one doesn't exist"""
        # Check if parent already exists with this email
        existing_user = await self.db.execute(
            select(User).where(User.email == parent_data.email)
        )
        existing_user = existing_user.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="An account with this email already exists"
            )

        # Create new user account
        temp_password = generate_temporary_password()
        user = User(
            email=parent_data.email,
            password_hash=get_password_hash(temp_password),
            role="parent",
            is_active=True,
            name=parent_data.name
        )
        self.db.add(user)
        await self.db.flush()

        # Create parent profile
        parent = Parent(
            name=parent_data.name,
            email=parent_data.email,
            phone=parent_data.phone,
            address=parent_data.address,
            school_id=parent_data.school_id,
            user_id=user.id
        )
        self.db.add(parent)
        await self.db.commit()
        await self.db.refresh(parent)

        # Send welcome email with credentials
        await self.send_welcome_email(parent.email, temp_password)
        
        return parent

    async def generate_activation_link(self, parent_id: int) -> str:
        """Generate a secure activation link for parent account"""
        token_data = {
            "parent_id": parent_id,
            "exp": datetime.utcnow() + settings.ACTIVATION_TOKEN_EXPIRE_MINUTES,
            "type": "parent_activation"
        }
        
        token = jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return f"{settings.FRONTEND_URL}/parent/activate?token={token}"

    async def send_welcome_email(self, email: str, temp_password: str):
        """Send welcome email to parent with temporary credentials"""
        subject = "Welcome to School Management System - Parent Account"
        body = f"""
        Dear Parent,

        Welcome to the School Management System. An account has been created for you to track your child's attendance and academic progress.

        Your login credentials:
        Email: {email}
        Temporary Password: {temp_password}

        Please log in and change your password immediately for security purposes.

        Best regards,
        School Management Team
        """
        
        await send_email(
            recipient_email=email,
            subject=subject,
            body=body
        )

    async def resend_credentials(self, parent_email: str):
        """Resend credentials to existing parent"""
        # Find parent account
        parent = await self.db.execute(
            select(Parent).join(User).where(Parent.email == parent_email)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent:
            raise HTTPException(
                status_code=404,
                detail="Parent account not found"
            )

        # Generate new temporary password
        temp_password = generate_temporary_password()
        
        # Update password in database
        parent.user.password_hash = get_password_hash(temp_password)
        await self.db.commit()

        # Send new credentials
        await self.send_welcome_email(parent_email, temp_password)
        
        return {"message": "New credentials sent successfully"}

    async def get_children(self, parent_id: int):
        """Get all children associated with a parent"""
        children = await self.db.execute(
            select(Student)
            .where(Student.parent_id == parent_id)
        )
        return children.scalars().all()

    async def verify_parent_access(self, parent_id: int, student_id: int) -> bool:
        """Verify if a parent has access to a student's information"""
        student = await self.db.execute(
            select(Student)
            .where(
                Student.id == student_id,
                Student.parent_id == parent_id
            )
        )
        return bool(student.scalar_one_or_none())
    
    async def update_parent_profile(self, parent_id: int, update_data: ParentUpdate) -> Parent:
        """Update parent profile information"""
        parent = await self.db.get(Parent, parent_id)
        if not parent:
            raise HTTPException(
                status_code=404,
                detail="Parent account not found"
            )

        # Update only the fields that have been set
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(parent, key, value)

        await self.db.commit()
        await self.db.refresh(parent)
        return parent