from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Union


class StudentCreate(BaseModel):
    name: str
    admission_number: str
    photo: Optional[str] = None
    gender: Optional[str] = None
    fingerprint: Optional[str] = None
    date_of_birth: date
    date_of_joining: Optional[date] = None
    address: Optional[str] = None
    password: str
    school_id: int
    class_id: int
    stream_id: Optional[int] = None
    parent_id: Optional[int] = None

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    photo: Optional[str] = None
    gender: Optional[str] = None
    fingerprint: Optional[str] = None
    date_of_birth: Optional[date] = None
    date_of_joining: Optional[date] = None
    address: Optional[str] = None
    class_id: Optional[int] = None
    stream_id: Optional[int] = None
    parent_id: Optional[int] = None

class StudentRegistrationRequest(BaseModel):
    # Student Information
    name: str = Field(..., description="Full name of the student")
    admNo: str = Field(..., description="Unique admission number")
    photo: Optional[str] = Field(None, description="Student's photo")
    gender: Optional[str] = Field(None, description="Student's gender")
    fingerprint: Optional[str] = Field(None, description="Student's fingerprint data")
    date_of_birth: date = Field(..., description="Date of birth")
    date_of_joining: Optional[date] = Field(..., description="Date of joining")
    address: Optional[str] = Field(None, description="Student's address")
    class_id: int = Field(..., description="ID of the class")
    stream_id: Optional[int] = Field(None, description="ID of the stream")
    
    # Parent/Guardian Information
    id_number: int = Field(..., description="ID of the parent/guardian")
    parent_name: str = Field(..., description="Parent's full name")
    parent_phone: str = Field(..., description="Parent's phone number")
    parent_email: EmailStr = Field(..., description="Parent's email address")
    relationship: str = Field(..., description="Relationship with the student")

    class Config:
        from_attributes = True