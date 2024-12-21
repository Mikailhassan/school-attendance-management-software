from pydantic import BaseModel, EmailStr
from typing import Optional

class SchoolBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    address: Optional[str] = None

    class Config:
        from_attributes = True

class StreamBase(BaseModel):
    name: str
    form: str
