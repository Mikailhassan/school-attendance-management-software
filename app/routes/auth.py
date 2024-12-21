from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.schemas import RegisterRequest, UserUpdateRequest, PasswordResetRequest
from app.models import User
from app.dependencies import get_db

router = APIRouter()

# Initialize AuthService with DB dependency
def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db=db)

@router.post("/register", response_model=User)
async def register(
    request: RegisterRequest,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user.
    """
    user = await auth_service.register_user(request, language)
    return user

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login and obtain JWT access and refresh tokens.
    """
    access_token, refresh_token, role = await auth_service.authenticate_user(
        form_data.username, form_data.password, language
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "role": role}

@router.post("/password-reset")
async def password_reset(
    email: str,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Generate a password reset token and send it to the user's email.
    """
    reset_token = await auth_service.generate_password_reset_token(email)
    return {"reset_token": reset_token}

@router.post("/reset-password")
async def reset_password(
    reset_token: str,
    new_password: str,
    language: str = 'en',
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Reset the password using the reset token.
    """
    success = await auth_service.reset_password(reset_token, new_password, language)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed"
        )
    return {"msg": "Password reset successful"}

@router.put("/update-profile", response_model=User)
async def update_profile(
    user_id: int,
    update_request: UserUpdateRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update user profile information.
    """
    user = await auth_service.update_user_profile(user_id, update_request)
    return user

@router.post("/logout")
async def logout(
    token: str,
    user_id: int,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Invalidate the user's token.
    """
    await auth_service.invalidate_token(token, user_id)
    return {"msg": "Logged out successfully"}

@router.post("/refresh-token")
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh the access token using a valid refresh token.
    """
    new_access_token = await auth_service.refresh_access_token(refresh_token)
    return {"access_token": new_access_token}

@router.get("/users", response_model=List[User])
async def list_users(
    school_id: int = None,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    List all users, optionally filtering by school.
    """
    users = await auth_service.list_users(school_id)
    return users
