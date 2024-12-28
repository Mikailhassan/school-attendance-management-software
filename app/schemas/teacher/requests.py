# app/  schemas/  teacher/  requests.py
from pydantic import BaseModel, validator, EmailStr
from datetime import date
from typing import Optional
from .base import TeacherBase

class TeacherCreate(TeacherBase):
    password: str
    school_id: int

class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None  # Ensure email follows proper format
    phone: Optional[str] = None  # Add phone number validation if needed
    tsc_number: Optional[str] = None

    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.isdigit():
            raise ValueError('Phone number should only contain digits')
        return v

class TeacherRegistrationRequest(BaseModel):
    name: str
    email: EmailStr  
    password: str
    phone: str
    tsc_number: str
    gender: str
    date_of_joining: date
    school_id: int

    @validator('gender')
    def validate_gender(cls, v):
        if v not in ('Male', 'Female', 'Other'):
            raise ValueError('Gender must be either Male, Female, or Other')
        return v

    @validator('date_of_joining')
    def validate_date_of_joining(cls, v):
        if v > date.today():
            raise ValueError("Date of joining cannot be in the future")
        return v
