# app/schemas/auth/responses.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.schemas.user.role import UserRoleEnum
from app.schemas.user.responses import UserResponse
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
    access_token: str
    refresh_token: str
    user: dict
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "role": "teacher",
                    "is_active": True,
                    "phone": "+1-555-123-4567",
                    "school_id": 1,
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_login": "2024-12-31T00:00:00Z"
                },
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }

    

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
