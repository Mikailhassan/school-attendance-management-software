# app/schemas/attendance/responses.py
from .base import AttendanceBase
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional

class Attendance(AttendanceBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AttendanceResponse(BaseModel):
    user_id: str
    check_type: str
    timestamp: str
    message: Optional[str] = None

class WeeklyAttendanceResponse(BaseModel):
    week_start_date: date
    week_end_date: date
    attendance_records: List[Attendance]

class PeriodAttendanceResponse(BaseModel):
    start_date: date
    end_date: date
    attendance_records: List[Attendance]
