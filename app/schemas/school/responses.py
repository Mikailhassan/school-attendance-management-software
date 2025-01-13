from pydantic import BaseModel, EmailStr, AnyUrl
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# Reusing enums from the request models
class SchoolType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    MIXED = "mixed"
    TECHNICAL = "technical"
    VOCATIONAL = "vocational"

class SchoolStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class ClassRangeResponse(BaseModel):
    start: str
    end: str

class SchoolAdminResponse(BaseModel):
    id: int
    email: EmailStr
    phone: str
    status: str
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

class SchoolResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    address: str
    school_type: SchoolType
    website: Optional[AnyUrl] = None
    registration_number: str
    status: SchoolStatus
    county: Optional[str] = None
    class_system: str
    class_range: ClassRangeResponse
    postal_code: Optional[str] = None
    extra_info: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    admin: SchoolAdminResponse

class SchoolListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[SchoolResponse]

class SessionResponse(BaseModel):
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    is_current: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class SessionListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[SessionResponse]

class ClassResponse(BaseModel):
    id: int
    name: str
   

class ClassListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[ClassResponse]

class StreamResponse(BaseModel):
    id: int
    name: str
    class_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class StreamListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[StreamResponse]

# Generic response models for common operations
class MessageResponse(BaseModel):
    message: str
    
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

class ValidationErrorResponse(BaseModel):
    error: str
    detail: Dict[str, List[str]]

# Response model for bulk operations
class BulkOperationResponse(BaseModel):
    success: int
    failed: int
    errors: Optional[List[Dict[str, Any]]] = None
class SchoolDetailResponse(SchoolResponse):
    current_session: Optional[SessionResponse] = None
    classes: List[ClassResponse] = []
    total_students: int
    total_teachers: int
    total_streams: int

    class Config:
        from_attributes = True
        
        
class ClassStatisticsResponse(BaseModel):
    class_name: str
    total_streams: int
    total_students: int
    class_id: int
    school_id: int

    class Config:
        from_attributes = True                