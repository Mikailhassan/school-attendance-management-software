# app/schemas/school/responses.py
from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from .requests import SchoolType

class StreamResponse(BaseModel):
    id: int
    name: str
    class_id: int
    capacity: Optional[int] = None
    teacher_id: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ClassResponse(BaseModel):
    id: int
    name: str
    level: int
    session_id: int
    description: Optional[str] = None
    capacity: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    streams: List[StreamResponse] = []

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: int
    name: str
    school_id: int
    start_date: datetime
    end_date: datetime
    is_current: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    classes: List[ClassResponse] = []

    class Config:
        from_attributes = True

class SchoolResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    address: str
    registration_number: str
    school_type: SchoolType
    website: Optional[HttpUrl] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class SchoolDetailResponse(SchoolResponse):
    current_session: Optional[SessionResponse] = None
    classes: List[ClassResponse] = []
    total_students: int
    total_teachers: int
    total_streams: int

    class Config:
        from_attributes = True