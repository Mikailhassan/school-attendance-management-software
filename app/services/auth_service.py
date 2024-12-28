from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.services.registration_service import RegistrationService

from .base_service import BaseService
from app.core.config import settings, get_jwt_settings
from app.core.logging import logger
from app.models import User, RevokedToken
from app.schemas import RegisterRequest, UserUpdateRequest, PasswordResetRequest
from app.services.email_service import EmailService
from app.services.fingerprint_service import FingerprintService

class AuthService(BaseService):
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def __init__(self, db: AsyncSession):
        self.db = db
        self.fingerprint_service = FingerprintService(db)
        self._email_service = None
        self.jwt_settings = get_jwt_settings()
    
    @property
    def email_service(self) -> EmailService:
        """Lazy load email service only when needed"""
        if self._email_service is None:
            self._email_service = EmailService()
        return self._email_service

    async def hash_password(self, password: str) -> str:
        """
        Securely hash a password.
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        """
        Verify a plain text password against its hash.
        """
        return self.pwd_context.verify(plain_password, password_hash)

    async def create_access_token(
        self, 
        data: dict, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token with optional expiration.
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.jwt_settings["access_token_expire_minutes"])
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(
            to_encode, 
            self.jwt_settings["secret_key"], 
            algorithm=self.jwt_settings["algorithm"]
        )

    async def create_refresh_token(
        self, 
        data: dict, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a refresh token with optional expiration.
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.jwt_settings["refresh_token_expire_days"])
        
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(
            to_encode, 
            self.jwt_settings["secret_key"], 
            algorithm=self.jwt_settings["algorithm"]
        )

    async def authenticate_user(
        self, 
        email: str, 
        password: str, 
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Comprehensive user authentication with token generation.
        Returns tokens and user information.
        """
        # Find user by email
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        # Validate user and password
        if not user or not self.verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials" if language == 'en' else "بيانات اعتماد غير صالحة"
            )
        
        # Check user account status
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive" if language == 'en' else "الحساب غير نشط"
            )
        
        # Generate tokens
        access_token = await self.create_access_token(
            data={"sub": str(user.id), "role": user.role}
        )
        refresh_token = await self.create_refresh_token(
            data={"sub": str(user.id), "role": user.role}
        )
        
        logger.info(f"User authenticated: {email}")
        
        # Return complete authentication response
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "role": user.role,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }



    async def generate_password_reset_token(self, email: str) -> str:
        """
        Generate a secure password reset token.
        """
        # Find user by email
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate reset token
        reset_token = await self.create_access_token(
            data={"sub": str(user.id), "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # Send reset email
        await self.email_service.send_password_reset_email(
            user.email, 
            reset_token
        )
        
        logger.info(f"Password reset token generated for: {email}")
        return reset_token

    async def reset_password(
        self, 
        reset_token: str, 
        new_password: str, 
        language: str = 'en'
    ) -> bool:
        """
        Reset user password using a valid reset token.
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                reset_token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # Validate token type
            if payload.get("type") != "password_reset":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid reset token"
                )
            
            user_id = int(payload.get("sub"))
            
            # Find user
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Validate new password
            if len(new_password) < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password too short" if language == 'en' else "كلمة المرور قصيرة جدًا"
                )
            
            # Hash and update password
            hashed_password = await self.hash_password(new_password)
            user.hashed_password = hashed_password
            
            await self.db.commit()
            
            logger.info(f"Password reset successful for user ID: {user_id}")
            return True
        
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

    async def update_user_profile(
        self, 
        user_id: int, 
        update_request: UserUpdateRequest
    ) -> User:
        """
        Update user profile information.
        """
        # Find user
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields if provided
        if update_request.name:
            user.name = update_request.name
        
        if update_request.email:
            # Check if email is already in use
            existing_email_query = select(User).where(User.email == update_request.email)
            existing_email_result = await self.db.execute(existing_email_query)
            if existing_email_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
            user.email = update_request.email
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"User profile updated: {user.email}")
        return user

    async def invalidate_token(self, token: str, user_id: int) -> None:
        """
        Invalidate a token by adding it to revoked tokens.
        """
        revoked_token = RevokedToken(
            token=token, 
            user_id=user_id, 
            revoked_at=datetime.utcnow()
        )
        
        self.db.add(revoked_token)
        await self.db.commit()
        
        logger.info(f"Token invalidated for user ID: {user_id}")

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Refresh access token using a valid refresh token.
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token, 
                self.jwt_settings["secret_key"], 
                algorithms=[self.jwt_settings["algorithm"]]
            )
            
            # Validate token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid refresh token"
                )
            
            user_id = payload.get("sub")
            user_role = payload.get("role")
            
            # Create new access token
            new_access_token = await self.create_access_token(
                data={"sub": user_id, "role": user_role}
            )
            
            return new_access_token
        
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

    async def list_users(
        self, 
        school_id: Optional[int] = None
    ) -> List[User]:
        """
        List users with optional school filtering.
        """
        if school_id:
            query = select(User).where(User.school_id == school_id)
        else:
            query = select(User)
        
        result = await self.db.execute(query)
        return result.scalars().all()