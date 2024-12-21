from pydantic import BaseModel
from typing import Optional
from ..user.base import UserBase  # Import UserBase

class StudentBase(UserBase):
    admission_number: str
    form: str
    stream: Optional[str] = None

    class Config:
        from_attributes = True
