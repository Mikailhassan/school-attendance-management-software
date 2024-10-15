from pydantic import BaseModel, EmailStr, validator
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Generic, TypeVar
from enum import Enum

# User Roles Enumeration
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"

# Token Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[UserRole] = None

# Login Request Model
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Base User Model
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None

    class Config:
        from_attributes = True

# User Creation Model
class UserCreate(UserBase):
    password: str
    role: UserRole
    school_id: Optional[int] = None

# User Response Model
class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# User Update Model
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True

# Password Change Model
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# Teacher Models
class TeacherBase(UserBase):
    tsc_number: str
    gender: str
    date_of_joining: date

    @validator('gender')
    def validate_gender(cls, v):
        if v not in ('Male', 'Female', 'Other'):
            raise ValueError('Gender must be either Male, Female, or Other')
        return v

    @validator('tsc_number')
    def validate_tsc_number(cls, v):
        if len(v) < 1:
            raise ValueError('TSC number must not be empty')
        return v

    class Config:
        from_attributes = True

class Teacher(TeacherBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class TeacherCreate(TeacherBase):
    password: str
    school_id: int

class TeacherResponse(TeacherBase):
    id: int
    user_id: int
    school_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TeacherUpdate(UserUpdate):
    tsc_number: Optional[str] = None

# Student Models
class StudentBase(UserBase):
    admission_number: str
    form: str
    stream: Optional[str] = None

    class Config:
        from_attributes = True

class StudentCreate(StudentBase):
    password: str
    school_id: int

class StudentResponse(StudentBase):
    id: int
    user_id: int
    school_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StudentUpdate(UserUpdate):
    form: Optional[str] = None
    stream: Optional[str] = None

# Parent Models
class ParentBase(UserBase):
    pass

class Parent(ParentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class ParentCreate(ParentBase):
    password: str

class ParentResponse(ParentBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: List[StudentResponse] = []

    class Config:
        from_attributes = True

class ParentUpdate(UserUpdate):
    pass

# School Models
class SchoolBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None

    class Config:
        from_attributes = True

class SchoolCreate(SchoolBase):
    pass

class School(SchoolBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SchoolUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True

# Stream Models
class StreamBase(BaseModel):
    name: str
    form: str

class StreamCreate(StreamBase):
    pass

class StreamResponse(StreamBase):
    id: int
    school_id: int

    class Config:
        from_attributes = True

# Attendance Models
class AttendanceBase(BaseModel):
    user_id: int
    school_id: int
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    is_present: bool = False

    class Config:
        from_attributes = True

class AttendanceCreate(AttendanceBase):
    pass

class Attendance(AttendanceBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Attendance Request Model
class AttendanceRequest(BaseModel):
    user_id: int
    school_id: int
    check_in_time: datetime
    check_out_time: Optional[datetime] = None

# Attendance Response Models
class WeeklyAttendanceResponse(BaseModel):
    week_start_date: date
    week_end_date: date
    attendance_records: List[Attendance]

class PeriodAttendanceResponse(BaseModel):
    start_date: date
    end_date: date
    attendance_records: List[Attendance]

# Fingerprint Models
class FingerprintBase(BaseModel):
    user_id: int

    class Config:
        from_attributes = True

class FingerprintCreate(FingerprintBase):
    fingerprint_data: bytes

class FingerprintResponse(FingerprintBase):
    id: int

    class Config:
        from_attributes = True

# Attendance Analytics Model
class AttendanceAnalytics(BaseModel):
    teacher_info: Dict[str, Any]
    student_info: Dict[str, Any]
    parent_info: Dict[str, Any]
    weekly_analysis: Optional[Dict[str, Any]]
    monthly_analysis: Optional[Dict[str, Any]]
    term_analysis: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

# Generic Page Model for Pagination
T = TypeVar('T')

class Page(Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int

    class Config:
        from_attributes = True

# Error Response Model
class ErrorResponse(BaseModel):
    detail: str

    class Config:
        from_attributes = True

# Registration Request Models
class TeacherRegistrationRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str
    tsc_number: str
    gender: str
    date_of_joining: date
    school_id: int

    @validator('gender')
    def validate_gender(cls, v):
        if v not in ('Male', 'Female', 'Other'):
            raise ValueError('Gender must be either Male, Female, or Other')
        return v

class StudentRegistrationRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    admission_number: str
    form: str
    stream: Optional[str] = None
    date_of_birth: Optional[date] = None
    school_id: int
