from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# School Response (includes sessions linked to the school)
class SchoolResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    sessions: List['SessionResponse']  # List of sessions tied to the school

    class Config:
        from_attributes = True

# Session Response (includes forms tied to the session)
class SessionResponse(BaseModel):
    id: int
    year: str  # e.g., "2024-2025"
    school_id: int
    forms: List['FormResponse']  # Forms linked to the session

    class Config:
        from_attributes = True

# Form Response (includes streams tied to the form)
class FormResponse(BaseModel):
    id: int
    name: str  # e.g., "Form 1", "Form 2"
    session_id: int
    streams: List['StreamResponse']  # Streams linked to the form

    class Config:
        from_attributes = True

# Stream Response (linked to form)
class StreamResponse(BaseModel):
    id: int
    name: str  # e.g., "Form 1A", "Form 1 North"
    form_id: int
    school_id: int  # Associated school

    class Config:
        from_attributes = True
