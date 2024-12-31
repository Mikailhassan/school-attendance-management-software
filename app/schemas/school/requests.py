# app/schemas/school/requests.py
from pydantic import BaseModel, EmailStr, Field, AnyUrl, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from .base import SchoolBase
import re

class SchoolType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BOTH = "both"
    TECHNICAL = "technical"
    VOCATIONAL = "vocational"

class SchoolStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"    

class ClassRange(BaseModel):
    start: int
    end: int    

class SchoolRegistrationRequest(SchoolBase):
    registration_number: str = Field(min_length=5, max_length=50)
    school_type: SchoolType
    website: Optional[AnyUrl] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Admin information
    admin_name: str = Field(min_length=2, max_length=100)
    admin_email: EmailStr
    admin_phone: str
    password: str = Field(min_length=8)

# Phone number validator function
def validate_phone(v: str) -> str:
    pattern = r"^(\+[1-9]{1,3}[- ]?)?\d{10}$"
    if not re.match(pattern, v):
        raise ValueError("Invalid phone number format")
    return v

class SchoolAdminRegistrationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str
    password: str = Field(min_length=8)
    school_registration_number: str = Field(min_length=5, max_length=50)
    school_id: int 

class SchoolFilterParams(BaseModel):
    """
    Schema for filtering schools in list operations
    """
    search: Optional[str] = None
    school_type: Optional[SchoolType] = None
    county: Optional[str] = None
    status: Optional[SchoolStatus] = None
    
    class Config:
        use_enum_values = True


class SchoolCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(examples=["+254722000000"])
    address: str = Field(min_length=5, max_length=255)
    registration_number: Optional[str] = Field(None, min_length=5, max_length=50)   
    school_type: SchoolType
    website: Optional[AnyUrl] = None
    county: Optional[str] = None
    class_system: str = Field(min_length=2, max_length=50)
    class_range: Dict[str, int]   
    postal_code: Optional[str] = None
    extra_info: Optional[Dict[str, Any]] = None



    def to_db_dict(self) -> dict:
        """Convert model to database-friendly dictionary"""
        data = self.model_dump()
        if data.get('website'):
            data['website'] = str(data['website'])
        return data

    @model_validator(mode='after')
    def validate_phone_number(self) -> 'SchoolCreateRequest':
        validate_phone(self.phone)
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "St. Mary's School",
                "email": "info@stmarys.edu",
                "phone": "+254722000000",
                "address": "123 Education Lane, Nairobi",
                "registration_number": "SCH-2024-001",
                "school_type": "secondary",
                "website": "https://www.stmarys.edu",
                "county": "Nairobi",
                "postal_code": "00100"
            }
        }
    }

class SchoolUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    website: Optional[AnyUrl] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    extra_info: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def validate_phone_number(self) -> 'SchoolUpdateRequest':
        if self.phone is not None:
            validate_phone(self.phone)
        return self

class SessionCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    start_date: datetime
    end_date: datetime
    is_current: bool = False
    description: Optional[str] = None

    @model_validator(mode='after')
    def validate_dates(self) -> 'SessionCreateRequest':
        if self.start_date >= self.end_date:
            raise ValueError('end_date must be after start_date')
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "2024-2025",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "is_current": True,
                "description": "Academic Year 2024-2025"
            }
        }
    }

class SessionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_current: Optional[bool] = None
    description: Optional[str] = None

class ClassCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Class 1",
               
            }
        }
    }

class ClassUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
  

class StreamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    class_id: int
    

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "1A",
                "class_id": 1,
                "description": "Class 1 Stream A"
            }
        }
    }

class StreamUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    class_id: Optional[int] = None