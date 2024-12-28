from pydantic import BaseModel, EmailStr
from typing import Optional
from .base import ParentBase

class ParentCreate(ParentBase):
    password: str  # Password for creating the parent profile

class ParentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    student_id: Optional[int] = None

class ParentRegistrationRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: str
    address: Optional[str] = None
    student_id: Optional[int]  # IDs of associated students
    school_id: int

    class Config:
        from_attributes = True
