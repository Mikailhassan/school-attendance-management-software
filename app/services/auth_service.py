from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Dict, Any

from app.database import get_db
from app.models import User

class AuthService:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    async def get_current_admin(self, token: str = Depends(oauth2_scheme)) -> User:
        user = self.db.query(User).filter(User.token == token).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user

    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not self.verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid credentials")
        
        # TODO: Generate and store a new token for the user
        # user.token = generate_token()
        # self.db.commit()

        return {"message": "Login successful", "user_id": user.id, "token": user.token}

    async def logout_user(self, current_user: User) -> Dict[str, str]:
        # TODO: Implement logout logic (e.g., invalidate the token)
        # current_user.token = None
        # self.db.commit()
        return {"message": "Logout successful"}

    async def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        if self._user_exists(user_data['email']):
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = User(
            name=user_data['name'],
            email=user_data['email'],
            phone=user_data.get('phone'),
            role=user_data['role'],
            password_hash=self.hash_password(user_data['password'])
        )

        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return {"message": "User registered successfully", "user_id": new_user.id}

    def _user_exists(self, email: str) -> bool:
        return self.db.query(User).filter(User.email == email).first() is not None

# Create global instances for convenience
pwd_context = AuthService.pwd_context
oauth2_scheme = AuthService.oauth2_scheme

# Helper functions that can be imported directly
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)