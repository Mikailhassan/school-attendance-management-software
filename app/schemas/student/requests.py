from pydantic import BaseModel, EmailStr, Field
from datetime import datetime,date
from typing import Optional, Union
from .base import StudentBase

# Student Creation Request (includes school_id, form, and stream)
class StudentCreate(BaseModel):
    password: str
    school_id: int
    class_id: int
    stream_id: Union[int, str, None] = None

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    class_id: Optional[int] = None
    stream_id: Optional[int] = None
    profile_picture: Optional[str] = None



class StudentRegistrationRequest(BaseModel):
    # Student Information
    name: str = Field(..., description="Full name of the student")
    email: EmailStr = Field(..., description="Valid email address for the student")
    password: str = Field(..., min_length=8, description="Password for student account")
    admission_number: str = Field(..., description="Unique admission number for the student")
    class_id: int = Field(..., description="ID of the class the student is enrolling in")
    stream_name: str = Field(..., description="Name of the stream (e.g., 'A', 'B', etc.)")
    date_of_birth: date = Field(..., description="Date of birth of the student")
    phone: Optional[str] = Field(None, description="Student's phone number (optional)")

    # Parent/Guardian Information
    parent_name: str = Field(..., description="Full name of the parent/guardian")
    parent_email: EmailStr = Field(..., description="Parent/guardian's email address")
    parent_phone: str = Field(..., description="Parent/guardian's phone number")
    parent_password: str = Field(
        ..., 
        min_length=8, 
        description="Password for parent account, must be at least 8 characters"
    )
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "name": "Ahmed Ali",
                "email": "ahmed.ali@example.com",
                "password": "SecurePassword123!",
                "admission_number": "1982",
                "class_id": 1,
                "stream_name": "B",
                "date_of_birth": "2008-05-14",
                "phone": "+254700000000",
                "parent_name": "Mohammed Ali",
                "parent_email": "mohammed.ali@example.com",
                "parent_phone": "+254711000000",
                "parent_password": "ParentPassword123!"
            }
        }




    class Config:
        from_attributes = True
