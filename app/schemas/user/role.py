# app/schemas/user/role.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

class UserRoleEnum(str, Enum):
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"
    # Configuration base class for consistent model settings
    class BaseConfig:
        from_attributes = True
        json_encoders = {
            Enum: lambda v: v.value,
            datetime: lambda v: v.isoformat()
        }
class RoleDetails(BaseModel):
    id: str = Field(..., description="Unique role identifier")
    name: str = Field(..., description="Human-readable role name")
    permissions: List[str] = Field(default_factory=list, description="List of role permissions")

    @classmethod
    def get_role_details(cls, role: UserRoleEnum) -> 'RoleDetails':
        role_mapping = {
            UserRoleEnum.SUPER_ADMIN: RoleDetails(
                id="super_admin",
                name="Super Administrator",
                permissions=["full_access", "system_management"]
            ),
            UserRoleEnum.SCHOOL_ADMIN: RoleDetails(
                id="school_admin", 
                name="School Administrator", 
                permissions=["school_management", "user_administration"]
            ),
            UserRoleEnum.TEACHER: RoleDetails(
                id="teacher",
                name="Teacher",
                permissions=["class_management", "attendance_tracking"]
            ),
            UserRoleEnum.STUDENT: RoleDetails(
                id="student", 
                name="Student", 
                permissions=["view_own_profile", "view_own_attendance"]
            ),
            UserRoleEnum.PARENT: RoleDetails(
                id="parent", 
                name="Parent", 
                permissions=["view_child_profile", "view_child_attendance"]
            )
        }
        return role_mapping.get(role, RoleDetails(
            id="unknown", 
            name="Unknown Role", 
            permissions=[]
        ))

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRoleEnum

class RegisterResponse(BaseModel):
    id: int = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User's email address")
    name: str = Field(..., description="User's full name")
    role: RoleDetails = Field(..., description="Detailed role information")

    @classmethod
    def from_user(cls, user):
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            role=RoleDetails.get_role_details(user.role)
        )

    class Config:
        from_attributes = True
        json_encoders = {
            Enum: lambda v: v.value
        }

class TokenRefreshRequest(BaseModel):
    refresh_token: str

