from pydantic import BaseModel
from datetime import datetime
from typing import Optional
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

class ParentResponse(ParentBaseResponse):
    created_at: datetime
    updated_at: Optional[datetime] = None

class ParentListResponse(BaseModel):
    parents: list[ParentResponse]
    total: int

    class Config:
        from_attributes = True
