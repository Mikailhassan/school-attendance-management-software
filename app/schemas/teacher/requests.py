from pydantic import BaseModel, EmailStr, validator, constr
from datetime import date
from typing import Optional
from enum import Enum

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class TeacherCreate(BaseModel):
    """Schema for creating a new teacher (internal use)"""
    name: constr(min_length=2, max_length=100)
    gender: Gender
    email: EmailStr
    phone: constr(min_length=9, max_length=13)
    date_of_joining: date
    date_of_birth: date
    tsc_number: str
    address: Optional[str] = None
   

    @validator('tsc_number')
    def validate_tsc_number(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('TSC number must be a 6-digit numeric value')
        return v

class TeacherUpdate(BaseModel):
    """Schema for updating teacher information (internal use)"""
    name: Optional[constr(min_length=2, max_length=100)] = None
    gender: Optional[Gender] = None
    phone: Optional[constr(min_length=9, max_length=13)] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None        

class TeacherRegistrationRequest(BaseModel):
    """Schema for registering a new teacher"""
    name: str
    gender: Gender
    email: EmailStr
    phone: str
    date_of_joining: date
    date_of_birth: date
    tsc_number: str
    address: Optional[str] = None
    
    @validator('date_of_birth')
    def validate_birth_date(cls, v):
        if v >= date.today():
            raise ValueError('Date of birth cannot be in the future')
        return v
    
    @validator('date_of_joining')
    def validate_joining_date(cls, v):
        if v > date.today():
            raise ValueError('Date of joining cannot be in the future')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        cleaned_phone = ''.join(filter(str.isdigit, v))
        if not (9 <= len(cleaned_phone) <= 13):
            raise ValueError('Phone number must be between 9 and 13 digits')
        return cleaned_phone

    @validator('tsc_number')
    def validate_tsc_number(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('TSC number must be a 6-digit numeric value')
        return v

class TeacherUpdateRequest(BaseModel):
    """Schema for updating an existing teacher"""
    name: Optional[str] = None
    gender: Optional[Gender] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is not None:
            cleaned_phone = ''.join(filter(str.isdigit, v))
            if not (9 <= len(cleaned_phone) <= 13):
                raise ValueError('Phone number must be between 9 and 13 digits')
            return cleaned_phone
        return v
    
