# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
# from app.services.auth_service import AuthService
from app.models.user import User
from app.core.security import verify_token
from app.schemas.auth.requests import UserInDB  

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UserInDB:  # Make sure return type is UserInDB
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        return UserInDB.from_orm(user)  # Convert SQLAlchemy model to Pydantic model
    except Exception:
        raise credentials_exception

async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin(
    current_user: UserInDB = Depends(get_current_active_user)  # Update type hint
) -> UserInDB:  # Update return type
    if current_user.role not in ['school_admin', 'super_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an admin"
        )
    return current_user

async def get_current_school_admin(
    current_user: UserInDB = Depends(get_current_active_user)  # Update type hint
) -> UserInDB:  # Update return type
    if current_user.role != 'school_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a school admin"
        )
    return current_user

async def get_current_super_admin(
    current_user: UserInDB = Depends(get_current_active_user)  # Update type hint
) -> UserInDB:  # Update return type
    if current_user.role != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a super admin"
        )
    return current_user

async def get_current_teacher(
    current_user: UserInDB = Depends(get_current_active_user)  # Update type hint
) -> UserInDB:  # Update return type
    if current_user.role != 'teacher':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a teacher"
        )
    return current_user