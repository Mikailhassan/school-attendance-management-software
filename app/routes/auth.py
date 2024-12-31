from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.utils import cookie_utils

from app.services import AuthService, RegistrationService, EmailService, SchoolService
from app.schemas import (
    RegisterRequest,
    RegisterResponse,
    UserUpdateRequest,
    UserResponse,
    LoginResponse,
    TokenResponse,
    SchoolCreateRequest,
)
from app.core.dependencies import (
    get_db,
    get_current_user,
    get_current_super_admin
)
from app.models import User
from app.core.config import settings

router = APIRouter(tags=["Authentication"])

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db=db)

def get_registration_service(db: Session = Depends(get_db)) -> RegistrationService:
    return RegistrationService(db=db)

def get_email_service(db: Session = Depends(get_db)) -> EmailService:
    return EmailService(db=db)

def get_cookie_settings(request: Request) -> Dict[str, Any]:
    """Get appropriate cookie settings based on environment"""
    host = request.headers.get("host", "").split(":")[0]
    is_localhost = host in ["localhost", "127.0.0.1"]
    
    return {
        "httponly": True,
        "secure": not is_localhost,
        "samesite": "lax" if is_localhost else "strict",
        "domain": None if is_localhost else f".{host}",
    }

@router.post("/register/school")
async def register_school(
    request: SchoolCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
) -> Dict[str, Any]:
    """Register a new school with admin account (Super Admin only)"""
    try:
        school_service = SchoolService(db)
        result = await school_service.create_school(request, background_tasks)
        
        return {
            "message": "School and admin account created successfully",
            "school_id": result["school_id"],
            "registration_number": result["registration_number"],
            "admin_email": result["admin_email"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service),
    email_service: EmailService = Depends(get_email_service)
) -> RegisterResponse:
    """Register users based on role"""
    if request.role in ["school", "school_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{request.role} registration must use appropriate endpoint"
        )
    
    try:
        registration_methods = {
            "teacher": registration_service.register_teacher,
            "student": registration_service.register_student,
            "parent": registration_service.register_parent
        }
        
        if request.role not in registration_methods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}"
            )
            
        register_func = registration_methods[request.role]
        
        # Handle specific registration logic
        if request.role == "parent":
            user = await register_func(request, request.student_id)
            access_link = f"{request.base_url}/parent-portal?token={user.generate_access_token()}"
            background_tasks.add_task(
                email_service.send_parent_portal_access,
                user.email,
                user.name,
                request.password,
                request.student_name,
                access_link,
                user.school.name
            )
        else:
            user = await register_func(request, request.school_id)
            if request.role == "teacher":
                background_tasks.add_task(
                    email_service.send_teacher_credentials,
                    user.email,
                    user.name,
                    request.password,
                    user.school.name
                )
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response = Response(),
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    try:
        if not request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request object is required"
            )

        # Pass both response AND request to authenticate_user
        auth_result = await auth_service.authenticate_user(
            form_data.username,  # This is the email
            form_data.password,
            response,
            request,  # Add the request parameter here
            language
        )
        
        return auth_result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/password-reset")
async def request_password_reset(
    email: str,
    background_tasks: BackgroundTasks,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, str]:
    """Request password reset token"""
    reset_token = await auth_service.generate_password_reset_token(email)
    return {"message": "Password reset instructions sent"}

@router.post("/reset-password")
async def reset_password(
    reset_token: str,
    new_password: str,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, str]:
    """Reset password using token"""
    success = await auth_service.reset_password(reset_token, new_password, language)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed"
        )
    return {"message": "Password reset successful"}

@router.put("/update-profile", response_model=UserResponse)
async def update_profile(
    user_id: int,
    update_request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """Update user profile information"""
    if current_user.id != user_id and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this profile"
        )
    return await auth_service.update_user_profile(user_id, update_request)

@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, str]:
    """Logout user and invalidate tokens"""
    token = auth_service.get_token_from_cookie(request)
    
    cookie_settings = get_cookie_settings(request)
    
    # Clear access token
    response.delete_cookie(
        key="access_token",
        path="/",
        **cookie_settings
    )
    
    # Clear refresh token
    refresh_cookie_settings = cookie_settings.copy()
    refresh_cookie_settings["path"] = "/api/v1/auth/refresh"
    response.delete_cookie(
        key="refresh_token",
        **refresh_cookie_settings
    )
    
    return await auth_service.logout(response, token, current_user.id)

@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Refresh access token using refresh token"""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    token_result = await auth_service.refresh_access_token(refresh_token, response)
    
    cookie_settings = get_cookie_settings(request)
    
    # Set new access token cookie
    access_expiration = datetime.utcnow() + timedelta(minutes=auth_service.access_token_expire_minutes)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token_result['access_token']}",
        expires=access_expiration,
        max_age=auth_service.access_token_expire_minutes * 60,
        path="/",
        **cookie_settings
    )
    
    return token_result

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    school_id: int = None,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
) -> List[UserResponse]:
    """List users, optionally filtered by school"""
    if current_user.role != "super_admin" and (
        school_id is None or school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to list users from other schools"
        )
    return await registration_service.get_school_users(school_id)

# Health check endpoint
@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}