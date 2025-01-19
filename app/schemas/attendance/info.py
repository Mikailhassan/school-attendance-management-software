# app/schemas/attendance/info.py
from pydantic import BaseModel
from datetime import datetime, date, time
from typing import Optional, List

class StreamInfo(BaseModel):
    id: int
    name: str  # e.g., "A", "B", "C"
    class_id: int
    total_students: int

    class Config:
        from_attributes = True

class ClassInfo(BaseModel):
    id: int
    name: str  
    school_id: int
    total_students: int
    streams: List[StreamInfo]

    class Config:
        from_attributes = True

class StudentInfo(BaseModel):
    id: int
    name: str
    admission_number: str
    class_id: int
    stream_id: int
    class_name: str  # e.g., "Form 1"
    stream_name: str  # e.g., "A"
    latest_attendance_status: Optional[str]
    last_attendance_date: Optional[datetime]

    @property
    def full_class_name(self) -> str:
        return f"{self.class_name} {self.stream_name}"  # e.g., "Form 1 A"

    class Config:
        from_attributes = True

class SessionInfo(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time
    start_date: date
    end_date: date
    weekdays: List[str]
    is_active: bool
    description: str | None = None

    class Config:
        from_attributes = True
        
class AttendanceInfo(BaseModel):
    student_id: int
    class_id: int  
    stream_id: int  
    session_id: int
    school_id: int
    date: datetime
    class_name: str
    stream_name: str
    status: str
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    remarks: Optional[str]

    class Config:
        from_attributes = True