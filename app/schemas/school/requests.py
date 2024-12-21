from pydantic import BaseModel, EmailStr
from typing import Optional

# School Admin Request for Creating and Updating Schools
class SchoolCreateRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None

class SchoolUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

# Session Models (linked to the school)
class SessionCreateRequest(BaseModel):
    year: str  # e.g., "2024-2025"
    school_id: int  # Identifies the school for which the session is created

class SessionUpdateRequest(BaseModel):
    year: Optional[str] = None
    school_id: Optional[int] = None

# Form Models (linked to the session)
class FormCreateRequest(BaseModel):
    name: str  # e.g., "Form 1", "Form 2"
    session_id: int  # Session ID from the school

class FormUpdateRequest(BaseModel):
    name: Optional[str] = None
    session_id: Optional[int] = None

# Stream Models (linked to the form)
class StreamCreateRequest(BaseModel):
    name: str  # e.g., "Form 1A", "Form 1 North"
    form_id: int  # Form ID under the session

class StreamUpdateRequest(BaseModel):
    name: Optional[str] = None
    form_id: Optional[int] = None
