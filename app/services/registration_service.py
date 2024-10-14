from fastapi import HTTPException, Depends, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
import os
import aiofiles
from pydantic import BaseModel, EmailStr, validator
from datetime import date

from app.models import User, Fingerprint, School
from app.database import get_db
from app.utils.password_utils import hash_password
from app.services.fingerprint_service import FingerprintService

class SchoolRegistrationRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    address: str

class UserRegistrationRequest(BaseModel):
    name: str
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class TeacherRegistrationRequest(UserRegistrationRequest):
    email: EmailStr
    phone: str
    tsc_number: str

class StudentRegistrationRequest(UserRegistrationRequest):
    admission_number: str
    date_of_birth: date
    stream: Optional[str] = None

class ParentRegistrationRequest(UserRegistrationRequest):
    email: EmailStr
    phone: str

class SchoolAdminRegistrationRequest(UserRegistrationRequest):
    email: EmailStr
    phone: str

class RegistrationService:
    def __init__(self, db: Session = Depends(get_db), fingerprint_service: FingerprintService = Depends(FingerprintService)):
        self.db = db
        self.fingerprint_service = fingerprint_service

    async def register_school(self, request: SchoolRegistrationRequest) -> School:
        try:
            new_school = School(**request.dict())
            self.db.add(new_school)
            self.db.commit()
            self.db.refresh(new_school)
            return new_school
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="School name or email already exists")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    async def register_user(self, request: UserRegistrationRequest, image: Optional[UploadFile] = None, role: str = 'student', school_id: Optional[int] = None) -> User:
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

    async def register_student(self, request: StudentRegistrationRequest, image: Optional[UploadFile] = None) -> User:
        return await self.register_user(request, image, 'student')

    def _create_user(self, request: UserRegistrationRequest, role: str, image_path: Optional[str], school_id: Optional[int]) -> User:
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
        fingerprint_template = await self.fingerprint_service.capture_fingerprint()
        if not fingerprint_template:
            raise HTTPException(status_code=400, detail="Fingerprint capture failed")
        return Fingerprint(user=user, fingerprint_template=fingerprint_template)

    async def _save_image(self, image: UploadFile) -> str:
        upload_dir = "uploaded_images"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, image.filename)

        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(await image.read())
            return file_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image saving failed: {str(e)}")

    async def register_teacher(self, request: TeacherRegistrationRequest, image: Optional[UploadFile] = None) -> User:
        return await self.register_user(request, image, 'teacher')

    async def register_parent(self, request: ParentRegistrationRequest, image: Optional[UploadFile] = None) -> User:
        return await self.register_user(request, image, 'parent')

    async def register_school_admin(self, request: SchoolAdminRegistrationRequest, school_id: int) -> User:
        return await self.register_user(request, role='school_admin', school_id=school_id)
