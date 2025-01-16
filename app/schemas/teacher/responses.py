from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import date, datetime
from typing import Optional
from enum import Enum
from ..user.base import UserBase

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class AttendanceSummary(BaseModel):
    """Schema for attendance summary"""
    total_days: int
    present_days: int
    absent_days: int
    attendance_percentage: float

class TeacherResponse(BaseModel):
    """Schema for teacher response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    gender: Gender
    email: EmailStr
    phone: str
    date_of_joining: date
    date_of_birth: date
    tsc_number: str
    address: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

class TeacherUpdateResponse(BaseModel):
    """Schema for the response after updating a teacher"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gender: Gender
    email: EmailStr
    phone: str
    date_of_joining: date
    date_of_birth: date
    tsc_number: str
    address: Optional[str] = None
    is_active: bool
    updated_at: date

class TeacherListResponse(BaseModel):
    """Schema for list of teachers response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gender: Gender
    email: EmailStr
    tsc_number: str
    phone: str
    date_of_joining: date

class TeacherDetailResponse(BaseModel):
    """Schema for detailed teacher response"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gender: Gender
    email: EmailStr
    phone: str
    date_of_joining: date
    date_of_birth: date
    tsc_number: str
    address: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    attendance_summary: Optional[AttendanceSummary] = None  # Updated to use proper type