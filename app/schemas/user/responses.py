# app/schemas/user/responses.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from ..enums import UserRole

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str

    class Config:
        from_attributes = True

class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    role: UserRole
    school_id: Optional[int] = None

    class Config:
        from_attributes = True

class UserUpdateResponse(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class RegisterResponse(BaseModel):
    user: UserResponse
    message: str = "Registration successful"