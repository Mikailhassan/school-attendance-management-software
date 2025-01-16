from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from pydantic.networks import EmailStr, AnyUrl
from typing import List
from .base import ParentBase

class ParentBaseResponse(ParentBase):
    id: int  # Parent ID

    class Config:
        from_attributes = True

class ParentCreateResponse(ParentBaseResponse):
    created_at: datetime
    updated_at: Optional[datetime] = None

class ParentDetailResponse(ParentBaseResponse):
    created_at: datetime
    updated_at: Optional[datetime] = None

class ParentUpdateResponse(ParentBaseResponse):
    updated_at: datetime

class ParentResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    school_id: int
    students: List[str]  
    user_id: int

    class Config:
        from_attributes = True

class ParentListResponse(BaseModel):
    parents: list[ParentResponse]
    total: int

    class Config:
        from_attributes = True
