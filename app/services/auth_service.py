# services/auth_service.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def get_current_admin(token: str = Depends(oauth2_scheme)):
    db = SessionLocal()
    # Verify the token (implement your own token validation logic)
    user = db.query(User).filter(User.token == token).first()  # Adjust as necessary
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user

async def login_user(request):
    db = SessionLocal()
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    return {"message": "Login successful", "user_id": user.id}

async def logout_user(current_user: str):
    # Logic to handle logout (e.g., clearing sessions or tokens)
    return {"message": "Logout successful"}

async def register_user(user_data):
    db = SessionLocal()
    
    # Check if the user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create a new user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        role=user_data.role,
        password_hash=hash_password(user_data.password)  # Hash the password
    )

    # Add the new user to the database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Refresh to get the latest data from the database
    
    return {"message": "User registered successfully", "user_id": new_user.id}
