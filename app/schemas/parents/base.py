# schemas/parent/base.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class ParentBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    student_id: int  # ID of the associated student
    school_id: int   # ID of the school

    class Config:
        from_attributes = True