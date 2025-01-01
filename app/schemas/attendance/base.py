# app/schemas/attendance/base.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AttendanceBase(BaseModel):
    status: str  # 'Present', 'Absent', 'Late'
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    remarks: Optional[str]

    class Config:
        from_attributes = True

