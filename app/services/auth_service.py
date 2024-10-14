from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.services.fingerprint_service import FingerprintService
from app.models import Fingerprint, User
from app.database import get_db
from passlib.context import CryptContext

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # Change this to a secure secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create a password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.fingerprint_service = FingerprintService(db)

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against the hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[User]:
        """Verify a JWT token and return the user."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            
            user = self.db.query(User).filter(User.id == int(user_id)).first()
            return user
        except JWTError:
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def capture_fingerprint(self) -> str:
        """Capture a fingerprint using the fingerprint service."""
        return self.fingerprint_service.capture_fingerprint()

    def verify_fingerprint(self, user_id: int) -> dict:
        """Verify the captured fingerprint with the stored template."""
        try:
            fingerprint_template = self.capture_fingerprint()
            verification_result = self.fingerprint_service.verify_fingerprint(fingerprint_template, user_id)
            return verification_result
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)

    def register_fingerprint(self, user_id: int) -> dict:
        """Register a new fingerprint for a user using the FingerprintService."""
        try:
            registration_result = self.fingerprint_service.register_fingerprint(user_id)
            return registration_result
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)

    def authenticate_with_fingerprint(self, user_id: int) -> Optional[dict]:
        """Authenticate a user with fingerprint and return access token."""
        verification_result = self.verify_fingerprint(user_id)
        if verification_result.get("success"):
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                access_token = self.create_access_token(
                    data={"sub": str(user.id)}
                )
                return {
                    "access_token": access_token,
                    "token_type": "bearer"
                }
        return None