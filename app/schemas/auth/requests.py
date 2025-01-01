from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from app.schemas.user.role import UserRoleEnum
from datetime import datetime

# Register Request Model - For registering a new user (with optional role)
class RegisterRequest(BaseModel):
    email: EmailStr  # Email address
    password: str  # User's password
    full_name: str  # User's full name
    role: Optional[UserRoleEnum] = None  # Optional role (could be 'admin', 'teacher', 'student', etc.)

    class Config:
        from_attributes = True

# Login Request Model - For logging in a user
class LoginRequest(BaseModel):
    email: EmailStr  # Email address
    password: str  # User's password

    class Config:
        from_attributes = True

# Password Reset Request Model - For resetting a user's password
class PasswordResetRequest(BaseModel):
    email: EmailStr  # Email address
    new_password: str  # New password
    confirm_password: str  # Confirm new password

    @validator("confirm_password")
    def passwords_match(cls, confirm_password, values):
        if "new_password" in values and confirm_password != values["new_password"]:
            raise ValueError("Passwords do not match")
        return confirm_password

    class Config:
        from_attributes = True

# Password Change Model - For changing a user's password
class PasswordChange(BaseModel):
    current_password: str  # Current password
    new_password: str  # New password
    confirm_password: str  # Confirm new password

    @validator("confirm_password")
    def passwords_match(cls, confirm_password, values):
        if "new_password" in values and confirm_password != values["new_password"]:
            raise ValueError("Passwords do not match")
        return confirm_password

    class Config:
        from_attributes = True

# User In Database Model - For returning user details from the database
class UserInDB(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    password_hash: str  # Changed from hashed_password to match the database column
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    school_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass

class AccountLockedException(Exception):
    """Raised when account is locked"""
    pass

class InvalidCredentialsException(Exception):
    """Raised when credentials are invalid"""
    pass

class AuthenticationError(Exception):
    """Raised for general authentication errors"""
    pass        