from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional
from .base import StudentBase

# Student Creation Request (includes school_id, form, and stream)
class StudentCreate(StudentBase):
    password: str
    school_id: int  # Identifies the school the student belongs to

# Student Update Request
class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    form: Optional[str] = None  # Form the student belongs to (e.g., "Form 1", "Form 2")
    stream: Optional[str] = None  # Stream the student belongs to (e.g., "Form 1A", "Form 1 North")
    profile_picture: Optional[str] = None  # Optional profile picture for the student

# Student Registration Request (handles admission, form, stream, and school)
class StudentRegistrationRequest(BaseModel):
    name: str  # Full name of the student
    email: EmailStr  # Email address
    password: str  # Password for the student account
    admission_number: str  # Unique admission number for the student
    form: str  # Form the student is in (e.g., "Form 1")
    stream: Optional[str] = None  # Optional stream for the student (e.g., "Form 1A")
    date_of_birth: Optional[date] = None  # Optional date of birth
    school_id: int  # ID of the school the student belongs to

    class Config:
        from_attributes = True
