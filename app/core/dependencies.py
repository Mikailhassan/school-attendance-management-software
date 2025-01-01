from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from typing import Tuple, Set, Callable, Awaitable, Optional
import os
from dotenv import load_dotenv

from app.models.user import User 
from app.models.school import School
from app.core.security import verify_token
from app.schemas.auth.requests import UserInDB
from app.services.auth_service import AuthService
from app.services.registration_service import RegistrationService
from app.services.email_service import EmailService
from app.services.school_service import SchoolService

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Initialize async database engine
async_engine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,
    future=True
)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Role hierarchies and permissions
ROLE_HIERARCHY = {
    'super_admin': {'school_admin', 'teacher', 'parent', 'student'},
    'school_admin': {'teacher', 'parent', 'student'},
    'teacher': {'student'},
    'parent': set(),  # Parents can only access their children's data
    'student': set()  # Students can only access their own data
}

# Database session management
async def get_db() -> AsyncSession:
    """Provide async database session"""
    AsyncSessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=async_engine,
    )
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Service providers
async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Provide AuthService instance"""
    return AuthService(db)  # Fixed: Direct instantiation instead of using create()

async def get_registration_service(db: AsyncSession = Depends(get_db)) -> RegistrationService:
    """Provide RegistrationService instance"""
    return RegistrationService(db)

async def get_email_service() -> EmailService:
    """Provide EmailService instance"""
    return EmailService()

async def get_school_service(db: AsyncSession = Depends(get_db)) -> SchoolService:
    """Provide SchoolService instance"""
    return SchoolService(db)

# User authentication and authorization
async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    try:
        # Debug logging
        print("All cookies:", request.cookies)
        auth_header = request.cookies.get("access_token")
        print("Raw auth cookie:", auth_header)
        
        if not auth_header:
            # Also check Authorization header as fallback
            auth_header = request.headers.get("Authorization")
            print("Auth header fallback:", auth_header)
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated - No token found"
                )
        
        # Clean up the token - handle both cookie and header cases
        if "Bearer" in auth_header:
            token = auth_header.replace("Bearer ", "").strip('"')
        else:
            token = auth_header.strip('"')
            
        print("Cleaned token:", token)
        
        # Verify token and get user
        try:
            user = await auth_service.get_current_user(token)
            print("User found:", user is not None)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token - User not found"
                )
            return user
            
        except Exception as token_error:
            print("Token verification error:", str(token_error))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(token_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print("Unexpected error:", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """Verify user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def check_role_hierarchy(user_role: str, required_role: str) -> bool:
    """Check if user_role has sufficient privileges for required_role"""
    if user_role == required_role:
        return True
    return required_role in ROLE_HIERARCHY.get(user_role, set())

async def verify_role_access(current_user: UserInDB, required_role: str) -> None:
    """Verify user has sufficient role privileges"""
    if not check_role_hierarchy(current_user.role, required_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User role '{current_user.role}' does not have required privileges"
        )

def get_current_role_user(role: str) -> Callable[[UserInDB], Awaitable[UserInDB]]:
    """Factory function for role-based dependencies"""
    async def role_dependency(
        current_user: UserInDB = Depends(get_current_active_user)
    ) -> UserInDB:
        await verify_role_access(current_user, role)
        return current_user
    return role_dependency

# Role-specific dependencies
get_current_super_admin = get_current_role_user('super_admin')
get_current_school_admin = get_current_role_user('school_admin')
get_current_teacher = get_current_role_user('teacher')
get_current_parent = get_current_role_user('parent')
get_current_student = get_current_role_user('student')

# School access verification
async def verify_school_access(
    registration_number: str,
    current_user: UserInDB,
    db: AsyncSession
) -> Tuple[UserInDB, School]:
    """
    Verify user has access to the specified school.
    Returns tuple of (user, school) if access is granted.
    """
    school_service = SchoolService(db)
    school = await school_service.get_school_by_registration(registration_number)
    
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # Super admins have access to all schools
    if current_user.role == "super_admin":
        return current_user, school
        
    # School admins and teachers can only access their own school
    if current_user.role in ['school_admin', 'teacher']:
        if current_user.school_id != school.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this school"
            )
        return current_user, school
        
    # Parents can access schools where their children are enrolled
    if current_user.role == 'parent':
        result = await db.execute(
            select(User).where(
                User.parent_id == current_user.id,
                User.school_id == school.id
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this school"
            )
        return current_user, school
        
    # Students can only access their own school
    if current_user.role == 'student':
        if current_user.school_id != school.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this school"
            )
        return current_user, school
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this school"
    )

# Optional school verification for endpoints that work with or without school context
async def get_optional_school(
    school_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
) -> Optional[School]:
    """Get school if school_id is provided, otherwise return None"""
    if school_id is None:
        return None
        
    school_service = SchoolService(db)
    school = await school_service.get_school_by_id(school_id)
    
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    return school