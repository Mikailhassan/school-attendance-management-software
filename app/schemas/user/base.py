# app/schemas/user/base.py
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional
from ..enums import UserRole 

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    school_id: int

class UserBaseSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    role: UserRole
    is_active: bool = True
    school_id: Optional[int] = None
    profile_picture: Optional[str] = None

    class Config:
        from_attributes = True