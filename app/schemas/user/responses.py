from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date

# Response Models for User
class UserResponse(BaseModel):
    email: EmailStr
    name: str
    role: str

    class Config:
        from_attributes = True

# Response Models for RegisterRequest
class RegisterResponse(BaseModel):
    email: EmailStr
    name: str
    role: Optional[str] = None

    class Config:
        from_attributes = True

# Response Models for UserUpdate
class UserUpdateResponse(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True

# Response Models for School Registration
class SchoolRegistrationResponse(BaseModel):
    name: str
    email: EmailStr
    phone: str
    address: str

    class Config:
        from_attributes = True

# User Base Response for Common Fields
class UserBaseResponse(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    role: Optional[str] = None

    class Config:
        from_attributes = True

# Teacher Response Model
class TeacherResponse(UserBaseResponse):
    tsc_number: str
    school_id: int

    class Config:
        from_attributes = True

# Student Response Model
class StudentResponse(UserBaseResponse):
    admission_number: str
    date_of_birth: date
    stream: Optional[str] = None
    school_id: int

    class Config:
        from_attributes = True

# Parent Response Model
class ParentResponse(UserBaseResponse):
    student_id: int
    school_id: int

    class Config:
        from_attributes = True

# School Admin Response Model
class SchoolAdminResponse(UserBaseResponse):
    school_id: int

    class Config:
        from_attributes = True

# Super Admin Response Model
class SuperAdminResponse(UserBaseResponse):
    # SuperAdmin does not need school_id because they manage all schools
    class Config:
        from_attributes = True
