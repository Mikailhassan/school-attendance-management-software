from fastapi import HTTPException, Depends, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
import os
import aiofiles

from app.schemas.registration import (
    SchoolRegistrationRequest, TeacherRegistrationRequest,
    StudentRegistrationRequest, ParentRegistrationRequest,
    SchoolAdminRegistrationRequest, SuperAdminRegistrationRequest,
    UserBaseSchema
)
from app.models import User, Fingerprint, School
from app.core.database import get_db
from app.utils.password_utils import hash_password
from app.core.security import get_current_user
# from app.services.fingerprint_service import FingerprintService

class RegistrationService:
    def __init__(
        self,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        fingerprint_service: FingerprintService = Depends(FingerprintService)
    ):
        self.db = db
        self.current_user = current_user
        self.fingerprint_service = fingerprint_service

    def _check_super_admin(self):
        if self.current_user.role != 'super_admin':
            raise HTTPException(
                status_code=403,
                detail="Only super admins can perform this action"
            )

    def _check_school_admin(self, school_id: int):
        if self.current_user.role != 'school_admin' or self.current_user.school_id != school_id:
            raise HTTPException(
                status_code=403,
                detail="Only school admins can perform this action for their school"
            )

    def _check_school_exists(self, school_id: int) -> School:
        school = self.db.query(School).filter(School.id == school_id).first()
        if not school:
            raise HTTPException(
                status_code=404,
                detail="School not found"
            )
        return school

    def _check_student_exists(self, student_id: int) -> User:
        student = self.db.query(User).filter(
            User.id == student_id,
            User.role == 'student'
        ).first()
        if not student:
            raise HTTPException(
                status_code=404,
                detail="Student not found"
            )
        return student

    async def register_school(self, request: SchoolRegistrationRequest) -> School:
        self._check_super_admin()
        try:
            new_school = School(**request.dict())
            self.db.add(new_school)
            self.db.commit()
            self.db.refresh(new_school)
            return new_school
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="School already exists")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    async def register_school_admin(
        self,
        request: SchoolAdminRegistrationRequest,
        school_id: int
    ) -> User:
        self._check_super_admin()
        school = self._check_school_exists(school_id)
        return await self.register_user(request, role='school_admin', school_id=school_id)

    async def register_teacher(
        self,
        request: TeacherRegistrationRequest,
        school_id: int,
        image: Optional[UploadFile] = None
    ) -> User:
        self._check_school_admin(school_id)
        return await self.register_user(request, image, 'teacher', school_id)

    async def register_student(
        self,
        request: StudentRegistrationRequest,
        school_id: int,
        image: Optional[UploadFile] = None
    ) -> User:
        self._check_school_admin(school_id)
        return await self.register_user(request, image, 'student', school_id)

    async def register_parent(
        self,
        request: ParentRegistrationRequest,
        student_id: int,
        image: Optional[UploadFile] = None
    ) -> User:
        student = self._check_student_exists(student_id)
        self._check_school_admin(student.school_id)
        parent = await self.register_user(request, image, 'parent', student.school_id)
        
        # Link parent to student
        student.parent_id = parent.id
        self.db.commit()
        return parent

    async def register_user(
        self,
        request: UserBaseSchema,
        image: Optional[UploadFile] = None,
        role: str = 'student',
        school_id: Optional[int] = None
    ) -> User:
        try:
            image_path = await self._save_image(image) if image else None
            user = self._create_user(request, role, image_path, school_id)
            fingerprint = await self._create_fingerprint(user)

            self.db.add(user)
            self.db.add(fingerprint)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="User already exists")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    def _create_user(
        self,
        request: UserBaseSchema,
        role: str,
        image_path: Optional[str],
        school_id: Optional[int]
    ) -> User:
        user_data = {
            'name': request.name,
            'role': role,
            'password_hash': hash_password(request.password),
            'image_path': image_path,
            'school_id': school_id
        }

        if isinstance(request, (TeacherRegistrationRequest, ParentRegistrationRequest, SchoolAdminRegistrationRequest)):
            user_data.update({
                'email': request.email,
                'phone': request.phone
            })
        
        if isinstance(request, TeacherRegistrationRequest):
            user_data['tsc_number'] = request.tsc_number
        elif isinstance(request, StudentRegistrationRequest):
            user_data.update({
                'admission_number': request.admission_number,
                'date_of_birth': request.date_of_birth,
                'stream': request.stream
            })

        return User(**user_data)

    async def _create_fingerprint(self, user: User) -> Fingerprint:
        try:
            fingerprint_template = await self.fingerprint_service.capture_fingerprint()
            if not fingerprint_template:
                raise HTTPException(status_code=400, detail="Fingerprint capture failed")
            return Fingerprint(user=user, fingerprint_template=fingerprint_template)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Fingerprint creation failed: {str(e)}"
            )

    async def _save_image(self, image: UploadFile) -> str:
        if not image:
            return None
            
        upload_dir = "uploaded_images"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        file_path = os.path.join(upload_dir, filename)

        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(await image.read())
            return file_path
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Image saving failed: {str(e)}"
            )

    async def get_school_users(
        self,
        school_id: int,
        role: Optional[str] = None
    ) -> List[User]:
        self._check_school_admin(school_id)
        query = self.db.query(User).filter(User.school_id == school_id)
        
        if role:
            query = query.filter(User.role == role)
            
        return query.all()

    async def delete_user(self, user_id: int):
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if self.current_user.role == 'school_admin':
            if user.school_id != self.current_user.school_id:
                raise HTTPException(
                    status_code=403,
                    detail="Can only delete users from your school"
                )
        elif self.current_user.role != 'super_admin':
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        try:
            # Delete associated fingerprint
            self.db.query(Fingerprint).filter(
                Fingerprint.user_id == user_id
            ).delete()
            
            # Delete image if exists
            if user.image_path and os.path.exists(user.image_path):
                os.remove(user.image_path)
                
            # Delete user
            self.db.delete(user)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting user: {str(e)}"
            )