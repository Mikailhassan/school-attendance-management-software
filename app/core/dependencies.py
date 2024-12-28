from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Tuple
from contextlib import asynccontextmanager

from app.core.database import get_db, AsyncSessionLocal
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.school import School  # Added School model import
from app.core.security import verify_token
from app.schemas.auth.requests import UserInDB
from app.services.registration_service import RegistrationService
from app.services.email_service import EmailService
from app.services.school_service import SchoolService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_db_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session)
) -> UserInDB:
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
            
        try:
            user_id_int = int(user_id)
        except ValueError:
            raise credentials_exception
            
        async with db.begin():
            result = await db.execute(
                select(User).where(User.id == user_id_int)
            )
            user = result.scalar_one_or_none()
            
            if user is None:
                raise credentials_exception
                
            return UserInDB.from_orm(user)
        
    except Exception as e:
        print(f"Error in get_current_user: {str(e)}")
        raise credentials_exception

async def get_registration_service(
    db: AsyncSession = Depends(get_db_session)
) -> RegistrationService:
    return RegistrationService(db)

async def get_email_service() -> EmailService:
    return EmailService()

async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    if current_user.role not in ['school_admin', 'super_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an admin"
        )
    return current_user

async def get_current_school_admin(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    if current_user.role != 'school_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a school admin"
        )
    return current_user

async def get_current_super_admin(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    if current_user.role != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a super admin"
        )
    return current_user

async def verify_school_access(
    registration_number: str,
    current_user: UserInDB,
    db: AsyncSession
) -> Tuple[UserInDB, School]:
    """Verify user has access to the specified school"""
    school_service = SchoolService(db)
    school = await school_service.get_school_by_registration(registration_number)
    
    # Check if super admin or user belongs to the school
    if current_user.role != "super_admin" and current_user.school_id != school.id:
        # If user is a parent, check if they have children in this school
        if current_user.role == 'parent':
            async with db.begin():
                result = await db.execute(
                    select(User).where(
                        User.parent_id == current_user.id,
                        User.school_id == school.id  # Using school.id instead of undefined school_id
                    )
                )
                children = result.scalar_one_or_none()
                
                if children:
                    return current_user, school
                
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this school"
        )
    
    return current_user, school