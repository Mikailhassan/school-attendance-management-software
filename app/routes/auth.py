from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    status, 
    Request,
    Path,
    Query
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import (
    RoleChecker, 
    verify_token, 
    generate_password_reset_token,
    get_current_user
)
from app.schemas import (
    LoginRequest, 
    LoginResponse, 
    RegisterRequest, 
    RegisterResponse, 
    TokenRefreshRequest, 
    TokenRefreshResponse,
    PasswordResetRequest,
    UserUpdateRequest,
    UserProfileResponse
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.models import User

# Role-Based Access Control Definitions
class RolePermissions:
    SUPER_ADMIN = ["super_admin"]
    SCHOOL_ADMIN = ["super_admin", "school_admin"]
    TEACHER = ["super_admin", "school_admin", "teacher"]
    ALL_USERS = ["super_admin", "school_admin", "teacher", "student"]

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Language Dependency
def get_accept_language(request: Request) -> str:
    """
    Extract preferred language from request headers.
    Defaults to English if not specified.
    """
    return request.headers.get('Accept-Language', 'en').split(',')[0]

@router.post(
    "/login", 
    response_model=LoginResponse, 
    status_code=status.HTTP_200_OK,
    summary="User Authentication",
    description="Authenticate user and generate access tokens"
)
async def login(
    request: LoginRequest, 
    db: Session = Depends(get_db),
    language: str = Depends(get_accept_language)
):
    """
    Authenticate a user with comprehensive error handling and logging.
    Supports multilingual error messages.
    """
    try:
        auth_service = AuthService(db=db)
        
        # Enhanced authentication with detailed logging
        token, refresh_token, role = await auth_service.authenticate_user(
            request.email, 
            request.password, 
            language=language
        )
        
        logger.info(f"User login successful: {request.email}")
        
        return LoginResponse(
            access_token=token, 
            refresh_token=refresh_token, 
            token_type="bearer", 
            role=role
        )
    except HTTPException as auth_error:
        logger.warning(f"Login attempt failed for {request.email}: {auth_error.detail}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Unexpected login error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Authentication service unavailable"
        )

@router.post(
    "/register", 
    response_model=RegisterResponse, 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(allowed_roles=RolePermissions.SUPER_ADMIN))],
    summary="User Registration",
    description="Register a new user with role-based access control"
)
async def register(
    request: RegisterRequest, 
    db: Session = Depends(get_db),
    language: str = Depends(get_accept_language)
):
    """
    Advanced user registration with comprehensive validation.
    """
    try:
        auth_service = AuthService(db=db)
        email_service = EmailService()
        
        # Register user with advanced validation
        user = await auth_service.register_user(request, language=language)
        
        # Optional: Send welcome email
        await email_service.send_welcome_email(user.email, language)
        
        logger.info(f"User registered successfully: {user.email}")
        
        return RegisterResponse(
            id=user.id, 
            email=user.email, 
            name=user.name, 
            role=user.role
        )
    except HTTPException as reg_error:
        logger.warning(f"Registration failed: {reg_error.detail}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Unexpected registration error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Registration service unavailable"
        )

@router.post(
    "/password-reset-request",
    status_code=status.HTTP_200_OK,
    summary="Initiate Password Reset",
    description="Generate and send password reset token"
)
async def initiate_password_reset(
    email: str = Query(..., description="User's email for password reset"),
    db: Session = Depends(get_db),
    language: str = Depends(get_accept_language)
):
    """
    Secure password reset token generation and email dispatch.
    """
    try:
        auth_service = AuthService(db=db)
        email_service = EmailService()
        
        reset_token = await auth_service.generate_password_reset_token(email)
        
        await email_service.send_password_reset_email(
            email, 
            reset_token, 
            language=language
        )
        
        logger.info(f"Password reset initiated for: {email}")
        return {"message": "Password reset link sent"}
    
    except HTTPException as reset_error:
        logger.warning(f"Password reset request failed: {reset_error.detail}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Unexpected password reset error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Password reset service unavailable"
        )

@router.post(
    "/password-reset",
    status_code=status.HTTP_200_OK,
    summary="Complete Password Reset",
    description="Reset password using reset token"
)
async def complete_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
    language: str = Depends(get_accept_language)
):
    """
    Complete password reset process.
    """
    try:
        auth_service = AuthService(db=db)
        
        await auth_service.reset_password(
            reset_request.token, 
            reset_request.new_password, 
            language=language
        )
        
        logger.info(f"Password reset completed successfully")
        return {"message": "Password reset successful"}
    
    except HTTPException as reset_error:
        logger.warning(f"Password reset failed: {reset_error.detail}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Unexpected password reset error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Password reset service unavailable"
        )

@router.post(
    "/token/refresh", 
    response_model=TokenRefreshResponse, 
    status_code=status.HTTP_200_OK
)
async def refresh_token(
    request: TokenRefreshRequest, 
    db: Session = Depends(get_db)
):
    """
    Refresh the access token using a valid refresh token.
    """
    try:
        auth_service = AuthService(db=db)
        new_access_token = await auth_service.refresh_access_token(request.refresh_token)
        
        return TokenRefreshResponse(
            access_token=new_access_token, 
            token_type="bearer"
        )
    except HTTPException as refresh_error:
        logger.warning(f"Token refresh failed: {refresh_error.detail}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Unexpected token refresh error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Token refresh service unavailable"
        )

@router.post(
    "/logout", 
    status_code=status.HTTP_200_OK
)
async def logout(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Log out the user by invalidating their tokens.
    """
    try:
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="No authorization token provided"
            )
        
        token = authorization.split(" ")[1] if len(authorization.split(" ")) > 1 else None
        
        auth_service = AuthService(db=db)
        await auth_service.invalidate_token(token, current_user.id)
        
        logger.info(f"User logged out: {current_user.email}")
        return {"message": "Successfully logged out"}
    except HTTPException as logout_error:
        logger.warning(f"Logout failed: {logout_error.detail}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Unexpected logout error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Logout service unavailable"
        )

@router.get(
    "/profile", 
    response_model=UserProfileResponse,
    dependencies=[Depends(RoleChecker(allowed_roles=RolePermissions.ALL_USERS))]
)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the current user's profile information.
    """
    return UserProfileResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        school_id=current_user.school_id
    )

@router.put(
    "/profile", 
    response_model=UserProfileResponse,
    dependencies=[Depends(RoleChecker(allowed_roles=RolePermissions.ALL_USERS))]
)
async def update_user_profile(
    update_request: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the current user's profile information.
    """
    try:
        auth_service = AuthService(db=db)
        updated_user = await auth_service.update_user_profile(
            current_user.id, 
            update_request
        )
        
        logger.info(f"User profile updated: {current_user.email}")
        
        return UserProfileResponse(
            id=updated_user.id,
            name=updated_user.name,
            email=updated_user.email,
            role=updated_user.role,
            school_id=updated_user.school_id
        )
    except HTTPException as update_error:
        logger.warning(f"Profile update failed: {update_error.detail}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Unexpected profile update error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Profile update service unavailable"
        )

# Additional admin-specific routes
@router.get(
    "/users", 
    response_model=List[UserProfileResponse],
    dependencies=[Depends(RoleChecker(allowed_roles=RolePermissions.SCHOOL_ADMIN))]
)
async def list_users(
    db: Session = Depends(get_db),
    school_id: Optional[int] = Query(None, description="Filter users by school")
):
    """
    List users with optional school filtering.
    """
    try:
        auth_service = AuthService(db=db)
        users = await auth_service.list_users(school_id)
        
        return [
            UserProfileResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                school_id=user.school_id
            ) for user in users
        ]
    except Exception as unexpected_error:
        logger.error(f"Unexpected user listing error: {unexpected_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="User listing service unavailable"
        )