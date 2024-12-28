from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.services.school_service import SchoolService
from sqlalchemy.orm import Session
from app.services import AuthService, RegistrationService, EmailService
from app.schemas import (
    RegisterRequest,
    RegisterResponse,
    UserUpdateRequest,
    PasswordResetRequest,
    UserResponse,
    LoginResponse,
    TokenResponse,
    SchoolRegistrationRequest,
    TeacherRegistrationRequest,
    StudentRegistrationRequest,
    ParentRegistrationRequest,
    SchoolAdminRegistrationRequest
)
from app.core.dependencies import (
    get_db, 
    get_current_user, 
    get_current_super_admin
)
from app.models import User

router = APIRouter(tags=["Authentication"])

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db=db)

def get_registration_service(
    db: AsyncSession = Depends(get_db)
) -> RegistrationService:
    return RegistrationService(db=db)

def get_email_service() -> EmailService:
    return EmailService()

@router.post("/register/school-admin")
async def register_school_admin(
    request: SchoolAdminRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    """Register a new school admin (Super Admin only)"""
    try:
        # First verify school exists using registration number
        school_service = SchoolService(db)
        school = await school_service.get_school_by_registration(
            request.school_registration_number
        )
        
        # Then proceed with registration
        registration_service = RegistrationService(db)
        user = await registration_service.register_school_admin(
            request,
            school.id  # Pass the actual school ID internally
        )
        
        # Send credentials email
        email_service = EmailService()
        await email_service.send_school_admin_credentials(
            user.email,
            user.name,
            request.password,
            school.name,
            school.registration_number
        )
        
        return {
            "message": "School admin registered successfully",
            "user_id": user.id,
            "school_registration_number": school.registration_number
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service),
    email_service: EmailService = Depends(get_email_service)
):
    """Register users based on role (except school admin)"""
    
    if not request.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role is required for registration"
        )
    
    if request.role == "school_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="School admin registration must use /register/school-admin endpoint"
        )
        
    try:
        if request.role == "school":
            school_request = SchoolRegistrationRequest(**request.dict())
            return await registration_service.register_school(school_request)
            
        elif request.role == "teacher":
            teacher_request = TeacherRegistrationRequest(**request.dict())
            user = await registration_service.register_teacher(
                teacher_request,
                request.school_id
            )
            await email_service.send_teacher_credentials(
                user.email,
                user.name,
                request.password,
                user.school.name
            )
            return user
            
        elif request.role == "student":
            student_request = StudentRegistrationRequest(**request.dict())
            return await registration_service.register_student(
                student_request,
                request.school_id
            )
            
        elif request.role == "parent":
            parent_request = ParentRegistrationRequest(**request.dict())
            user = await registration_service.register_parent(
                parent_request,
                request.student_id
            )
            access_link = f"{request.base_url}/parent-portal?token={user.generate_access_token()}"
            await email_service.send_parent_portal_access(
                user.email,
                user.name,
                request.password,
                request.student_name,
                access_link,
                user.school.name
            )
            return user
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login and obtain JWT access and refresh tokens."""
    return await auth_service.authenticate_user(
        form_data.username,
        form_data.password,
        language
    )

@router.post("/password-reset", response_model=dict)
async def password_reset(
    email: str,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service),
    email_service: EmailService = Depends(get_email_service)
):
    """Generate and send password reset token."""
    reset_token = await auth_service.generate_password_reset_token(email)
    return {"reset_token": reset_token}

@router.post("/reset-password", response_model=dict)
async def reset_password(
    reset_token: str,
    new_password: str,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
):
    """Reset password using token."""
    success = await auth_service.reset_password(reset_token, new_password, language)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed"
        )
    return {"msg": "Password reset successful"}

@router.put("/update-profile", response_model=UserResponse)
async def update_profile(
    user_id: int,
    update_request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user profile information."""
    if current_user.id != user_id and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this profile"
        )
    return await auth_service.update_user_profile(user_id, update_request)

@router.post("/logout", response_model=dict) 
async def logout(
    token: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Invalidate user token."""
    await auth_service.invalidate_token(token, current_user.id)
    return {"msg": "Logged out successfully"}

@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token."""
    new_access_token = await auth_service.refresh_access_token(refresh_token)
    return {"access_token": new_access_token}

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    school_id: int = None,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
):
    """List users, optionally filtered by school."""
    # Only super_admin can list all users, others are restricted to their school
    if current_user.role != "super_admin" and (
        school_id is None or school_id != current_user.school_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to list users from other schools"
        )
    return await registration_service.get_school_users(school_id)