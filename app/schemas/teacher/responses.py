# app/schemas/teacher/responses.py
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional
from ..user.base import UserBase  # Change this line

class TeacherBaseResponse(UserBase):
    id: int
    tsc_number: str
    gender: str
    date_of_joining: date

    class Config:
        from_attributes = True

class TeacherResponse(TeacherBaseResponse):
    created_at: date
    updated_at: Optional[date] = None

class TeacherUpdateResponse(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tsc_number: Optional[str] = None
    gender: Optional[str] = None
    date_of_joining: Optional[date] = None
    school_id: Optional[int] = None
    updated_at: date

    class Config:
        from_attributes = True

class TeacherListResponse(BaseModel):
    teachers: list[TeacherResponse]
    total: int

    class Config:
        from_attributes = True