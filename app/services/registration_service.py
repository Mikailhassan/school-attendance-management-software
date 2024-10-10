from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.models import User, Fingerprint
from app.database import get_db
from app.services.auth_service import hash_password
from app.services.fingerprint_service import FingerprintService

class RegistrationService:
    def __init__(self, db: Session = Depends(get_db), fingerprint_service: FingerprintService = Depends(FingerprintService)):
        self.db = db
        self.fingerprint_service = fingerprint_service

    async def register_user(self, request: Dict[str, Any], role: str) -> User:
        self._check_existing_user(request)
        
        user = self._create_user(request, role)
        fingerprint = await self._create_fingerprint(user)

        self.db.add(user)
        self.db.add(fingerprint)
        self.db.commit()
        self.db.refresh(user)

        return user

    def _check_existing_user(self, request: Dict[str, Any]):
        if 'email' in request:
            existing_user = self.db.query(User).filter(User.email == request['email']).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
        elif 'admission_number' in request:
            existing_student = self.db.query(User).filter(User.admission_number == request['admission_number']).first()
            if existing_student:
                raise HTTPException(status_code=400, detail="Admission number already registered")

    def _create_user(self, request: Dict[str, Any], role: str) -> User:
        user_data = {
            'name': request['name'],
            'role': role,
            'password_hash': hash_password(request['password'])
        }

        if role == 'teacher':
            user_data.update({
                'email': request['email'],
                'phone': request['phone'],
                'tsc_number': request['tsc_number']
            })
        elif role == 'student':
            user_data.update({
                'admission_number': request['admission_number'],
                'date_of_birth': request['date_of_birth']
            })
        elif role == 'parent':
            user_data.update({
                'email': request['email'],
                'phone': request['phone']
            })

        return User(**user_data)

    async def _create_fingerprint(self, user: User) -> Fingerprint:
        """Capture fingerprint and create a Fingerprint record."""
        fingerprint_template = await self.fingerprint_service.capture_fingerprint()
        if not fingerprint_template:
            raise HTTPException(status_code=400, detail="Fingerprint capture failed")
        return Fingerprint(user=user, fingerprint_template=fingerprint_template)

    async def register_teacher(self, request: Dict[str, Any]) -> User:
        return await self.register_user(request, 'teacher')

    async def register_student(self, request: Dict[str, Any]) -> User:
        return await self.register_user(request, 'student')

    async def register_parent(self, request: Dict[str, Any]) -> User:
        return await self.register_user(request, 'parent')
