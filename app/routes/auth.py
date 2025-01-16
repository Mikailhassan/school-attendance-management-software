from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    status, 
    Response, 
    Request, 
    BackgroundTasks
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.errors import (
    RateLimitExceeded,
    AccountLockedException,
    InvalidCredentialsException,
    AuthenticationError,
    ConfigurationError,
    get_error_message
)
from app.services import AuthService, RegistrationService, EmailService, SchoolService
from app.core.config import settings 
from app.services.auth_service import JWTSettings
from app.schemas import (
    RegisterRequest,
    RegisterResponse,
    UserUpdateRequest,
    UserResponse,
    LoginResponse,
    TokenResponse,
    SchoolCreateRequest,
    LoginRequest,
    TokenData
)
from app.core.dependencies import (
    get_db,
    get_current_user,
    get_current_super_admin,
    get_current_active_user
)
from app.models import User
from app.core.logging import logger
import uuid

router = APIRouter(tags=["Authentication"])

# Service dependencies
def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db=db)

def get_registration_service(db: AsyncSession = Depends(get_db)) -> RegistrationService:
    return RegistrationService(db=db)

def get_email_service(db: AsyncSession = Depends(get_db)) -> EmailService:
    return EmailService(db=db)

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service),
    email_service: EmailService = Depends(get_email_service)
) -> RegisterResponse:
    """Register new users based on role"""
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
@router.post("/verify-session")
async def verify_session(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    language: str = 'en'
) -> Dict[str, Any]:
    """Verify session validity and refresh if needed"""
    try:
        # Get token from request
        token = await auth_service.get_token_from_request(request)
        if not token:
            raise AuthenticationError("No token provided")

        # Try to validate the token and session
        payload = await auth_service.validate_token(token, language)
        
        # Get session info if available
        session = await auth_service.validate_session(payload.get('session_id'))
        
        # The session data already contains ISO-formatted datetime strings
        # so we don't need to call .isoformat() on them
        return {
            "valid": True,
            "payload": payload,
            "session": {
                "id": session.get("session_id") if session else None,
                "expires_at": session.get("expires_at") if session and session.get("expires_at") else None,
                "last_activity": session.get("last_activity") if session and session.get("last_activity") else None
            } if session else None
        }
        
    except AuthenticationError as e:
        logger.warning(f"Session verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "valid": False,
                "message": get_error_message("session_validation_failed", language),
                "code": "SESSION_INVALID"
            }
        )
    except Exception as e:
        logger.error(f"Session verification error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "valid": False,
                "message": get_error_message("unexpected_error", language),
                "code": "SERVER_ERROR"
            }
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """
    Authenticate user and generate access & refresh tokens
    """
    try:
        # Store language preference
        request.state.language = language
        
        # Basic input sanitization
        email = credentials.email.lower().strip()
        password = credentials.password.strip()
        
        # Get client info for logging/tracking
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        request_id = str(uuid.uuid4())
        
        # Enhanced logging for security tracking
        logger.info(
            "Login attempt initiated",
            extra={
                "request_id": request_id,
                "ip": client_ip,
                "user_agent": user_agent,
                "email_domain": email.split('@')[1] if '@' in email else None
            }
        )
        
        # Authenticate user and get login response
        login_response = await auth_service.authenticate_user(
            email=email,
            password=password,
            response=response,
            request=request,
            language=language
        )
        
        # Fixed: Use proper Pydantic model attribute access
        logger.info(
            "Login successful",
            extra={
                "request_id": request_id,
                "user_id": str(login_response.user.id),  # Changed from .get("id") to .id
                "ip": client_ip
            }
        )
        
        return login_response
            
    except (RateLimitExceeded, AccountLockedException) as e:
        logger.warning(
            "Login blocked due to rate limit or account lock",
            extra={
                "request_id": request_id,
                "ip": client_ip,
                "email": email,
                "reason": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
            headers={
                "Retry-After": str(auth_service.lockout_duration_minutes * 60),
                "X-Error-Code": "ACCOUNT_LOCKED"
            }
        )
    
    except InvalidCredentialsException as e:
        logger.warning(
            "Invalid credentials provided",
            extra={
                "request_id": request_id,
                "ip": client_ip,
                "email": email
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"X-Error-Code": "INVALID_CREDENTIALS"}
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error during login",
            exc_info=True,
            extra={
                "request_id": request_id if 'request_id' in locals() else None,
                "error_type": type(e).__name__,
                "ip": client_ip if 'client_ip' in locals() else None
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_error_message("unexpected_error", language),
            headers={"X-Error-Code": "SERVER_ERROR"}
        )
@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    language: str = 'en'
) -> TokenResponse:
    """Refresh access token using refresh token"""
    try:
        # Extract refresh token with improved error handling
        refresh_token = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ")[1]
        else:
            refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            logger.warning("No refresh token found in cookies or headers")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": get_error_message("refresh_token_not_found", language),
                    "code": "TOKEN_NOT_FOUND"
                }
            )

        # Get token response from auth service
        token_data = await auth_service.refresh_access_token(
            refresh_token=refresh_token,
            response=response,
            request=request,
            language=language
        )
        
        if not isinstance(token_data, dict):
            raise ValueError("Invalid token response format")
            
        # Create token response object
        token_response = TokenResponse(
            access_token=token_data["access_token"],
            token_type="bearer"
        )

        # Set cookie settings based on environment
        cookie_settings = {
            "httponly": True,
            "secure": settings.COOKIE_SECURE,  # True in production
            "samesite": "lax" if settings.DEBUG else "strict",
            "domain": settings.COOKIE_DOMAIN,
            "path": "/"
        }

        # Set access token cookie with proper formatting
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token_response.access_token}",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            **cookie_settings
        )
        
        logger.info("Token refresh successful")
        return token_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": get_error_message("token_refresh_failed", language),
                "code": "REFRESH_FAILED"
            }
        )
@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    language: str = 'en'
) -> Dict[str, str]:
    """Logout user and invalidate tokens"""
    try:
        token = await auth_service.get_token_from_request(request)
        return await auth_service.logout(token, response, request, language)
    except Exception as e:
        logger.error("Logout error", extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_error_message("logout_failed", language)
        )

@router.get("/validate-token")
async def validate_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    language: str = 'en'
) -> Dict[str, Any]:
    """Validate token and handle refresh if needed"""
    try:
        # Get access token from request
        access_token = await auth_service.get_token_from_request(request)
        if not access_token:
            raise AuthenticationError("No token provided")

        try:
            # First try to validate the access token
            payload = await auth_service.validate_token(access_token, language)
            return {
                "valid": True,
                "payload": payload
            }
        except AuthenticationError:
            # Access token is invalid/expired, try to use refresh token
            refresh_token = request.cookies.get("refresh_token")
            if not refresh_token:
                raise AuthenticationError("No refresh token available")

            # Try to refresh the access token
            refresh_result = await auth_service.refresh_access_token(
                refresh_token.replace("Bearer ", ""),
                response,
                request,
                language
            )

            return {
                "valid": True,
                "access_token": refresh_result["access_token"],
                "token_type": "bearer",
                "refreshed": True
            }

    except AuthenticationError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "valid": False,
                "message": get_error_message("token_validation_failed", language),
                "redirect": "/login"
            }
        )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_error_message("unexpected_error", language)
        )
@router.put("/update-profile", response_model=UserResponse)
async def update_profile(
    user_id: int,
    update_request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """Update user profile information"""
    try:
        if current_user.id != user_id and current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this profile"
            )
        return await auth_service.update_user_profile(user_id, update_request)
    except Exception as e:
        logger.error("Profile update error", extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    school_id: int = None,
    current_user: User = Depends(get_current_user),
    registration_service: RegistrationService = Depends(get_registration_service)
) -> List[UserResponse]:
    """List users, optionally filtered by school"""
    try:
        if current_user.role != "super_admin" and (
            school_id is None or school_id != current_user.school_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to list users from other schools"
            )
        return await registration_service.get_school_users(school_id)
    except Exception as e:
        logger.error("List users error", extra={"error_type": type(e).__name__})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}