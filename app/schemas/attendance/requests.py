from .base import AttendanceBase
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AttendanceCreate(AttendanceBase):
    pass

class AttendanceRequest(BaseModel):
    user_id: int
    school_id: int
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
