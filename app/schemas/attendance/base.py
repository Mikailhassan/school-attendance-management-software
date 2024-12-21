from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AttendanceBase(BaseModel):
    user_id: int
    school_id: int
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    is_present: bool = False

    class Config:
        from_attributes = True
