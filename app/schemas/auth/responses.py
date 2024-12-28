# app/schemas/auth/responses.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.schemas.user.role import UserRoleEnum
from datetime import datetime

# Base User Response Model (common fields for all user responses)
class UserBaseResponse(BaseModel):
    id: int  # Unique ID of the user
    email: EmailStr  # User's email address
    name: str  # User's full name
    role: UserRoleEnum  # User's role (e.g., admin, teacher, student)
    is_active: bool  # Whether the user is active or not
    school_id: Optional[int] = None  # School ID if the user is linked to a school
    created_at: datetime  # Timestamp of when the user was created
    updated_at: Optional[datetime] = None  # Timestamp of when the user was last updated

    class Config:
        from_attributes = True

# Response for a successful user login (includes a token for authentication)
class LoginResponse(BaseModel):
    access_token: str  # The access token generated after a successful login
    refresh_token: str  # The refresh token for obtaining new access tokens
    token_type: str = "bearer"  # Type of the token (Bearer)
    role: UserRoleEnum  # User's role from the token
    user: UserBaseResponse  # User details included in the response

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True

# Response for a successful user registration (after creating a new user)
class RegisterResponse(UserBaseResponse):
    created_at: datetime  # Timestamp when the user was created

    class Config:
        from_attributes = True

# Response for a user password reset (success indication)
class PasswordResetResponse(BaseModel):
    message: str = "Password reset successful"  # A message indicating success

    class Config:
        from_attributes = True

# Response for a user password change (success indication)
class PasswordChangeResponse(BaseModel):
    message: str = "Password changed successfully"  # A message indicating success

    class Config:
        from_attributes = True
