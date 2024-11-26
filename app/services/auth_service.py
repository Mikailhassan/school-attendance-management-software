from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.services.fingerprint_service import FingerprintService
from app.models import Fingerprint, User
from app.core.database import get_db
from passlib.context import CryptContext

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # Change this to a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create a password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.fingerprint_service = FingerprintService(db)

    async def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against the hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    async def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def verify_token(self, token: str) -> Optional[User]:
        """Verify a JWT token and return the user."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            
            query = select(User).where(User.id == int(user_id))
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            return user
        except JWTError:
            return None

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def capture_fingerprint(self) -> str:
        """Capture a fingerprint using the fingerprint service."""
        return await self.fingerprint_service.capture_fingerprint()

    async def verify_fingerprint(self, user_id: int) -> dict:
        """Verify the captured fingerprint with the stored template."""
        try:
            fingerprint_template = await self.capture_fingerprint()
            verification_result = await self.fingerprint_service.verify_fingerprint(fingerprint_template, user_id)
            return verification_result
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)

    async def register_fingerprint(self, user_id: int) -> dict:
        """Register a new fingerprint for a user using the FingerprintService."""
        try:
            registration_result = await self.fingerprint_service.register_fingerprint(user_id)
            return registration_result
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)

    async def authenticate_with_fingerprint(self, user_id: int) -> Optional[dict]:
        """Authenticate a user with fingerprint and return access token."""
        verification_result = await self.verify_fingerprint(user_id)
        if verification_result.get("success"):
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                access_token = await self.create_access_token(
                    data={"sub": str(user.id)}
                )
                return {
                    "access_token": access_token,
                    "token_type": "bearer"
                }
        return None

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by their ID."""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()