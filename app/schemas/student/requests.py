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
    password: Optional[str] = Field(None, min_length=8, description="Optional password for student account")
    admission_number: str = Field(..., description="Unique admission number for the student")
    class_id: int = Field(..., description="ID of the class the student is enrolling in")
    stream_name: Optional[str] = Field(..., description="Name of the stream (e.g., 'A', 'B', etc.)")
    date_of_birth: date = Field(..., description="Date of birth of the student")
    phone: Optional[str] = Field(None, description="Student's phone number")
    gender: Optional[str] = Field(None, description="Student's gender")
    address: Optional[str] = Field(None, description="Student's address")
    
    # Emergency Contact Information
    emergency_contact_name: Optional[str] = Field(None, description="Name of emergency contact")
    emergency_contact_phone: Optional[str] = Field(None, description="Phone number of emergency contact")
    emergency_contact_relationship: Optional[str] = Field(None, description="Relationship with emergency contact")

    # Parent/Guardian Information
    parent_name: str = Field(..., description="Full name of the parent/guardian")
    parent_email: EmailStr = Field(..., description="Parent/guardian's email address")
    parent_phone: str = Field(..., description="Parent/guardian's phone number")




    class Config:
        from_attributes = True
