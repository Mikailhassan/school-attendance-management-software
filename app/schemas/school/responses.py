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

from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime
from .requests import SchoolType, ClassRange

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
    class_system: str
    class_range: ClassRange
    postal_code: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra_info: Optional[Dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Saka Girls Secondary School",
                "email": "abdullahiwardere@gmail.com",
                "phone": "+254711997404",
                "address": "123 Saka Road, Northern County",
                "registration_number": "SGSS123",
                "school_type": "secondary",
                "website": "http://sakagirlssecondaryschool.com",
                "county": "Northern County",
                "class_system": "8-4-4",
                "class_range": {
                    "start": "Form 1",
                    "end": "Form 4"
                },
                "postal_code": "00100",
                "is_active": true,
                "created_at": "2024-03-19T12:00:00Z",
                "updated_at": "2024-03-19T12:00:00Z",
                "extra_info": {
                    "motto": "Education for a brighter future",
                    "established": "2005"
                }
            }
        }
    }

class SchoolDetailResponse(SchoolResponse):
    current_session: Optional[SessionResponse] = None
    classes: List[ClassResponse] = []
    total_students: int
    total_teachers: int
    total_streams: int

    class Config:
        from_attributes = True