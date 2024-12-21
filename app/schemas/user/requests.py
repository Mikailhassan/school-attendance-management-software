from pydantic import BaseModel, validator
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str  
    role: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str  
    role: Optional[str] = None    

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None  # Changed from full_name
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None    



class UserBaseSchema(BaseModel):
    name: str  
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    class Config:
        from_attributes = True

class TeacherRegistrationRequest(UserBaseSchema):
    email: EmailStr
    phone: str
    tsc_number: str
    school_id: int

class StudentRegistrationRequest(UserBaseSchema):
    admission_number: str
    date_of_birth: date
    stream: Optional[str] = None
    school_id: int

class ParentRegistrationRequest(UserBaseSchema):
    email: EmailStr
    phone: str
    student_id: int
    school_id: int

class SchoolAdminRegistrationRequest(UserBaseSchema):
    email: EmailStr
    phone: str
    school_id: int

class SuperAdminRegistrationRequest(UserBaseSchema):
    email: EmailStr
    phone: str
