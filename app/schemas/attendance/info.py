# app/schemas/attendance/info.py
from pydantic import BaseModel
from datetime import datetime
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
    name: str  # e.g., "Form 1", "Class 6", "Grade 8"
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
    start_time: datetime
    end_time: datetime
    status: str
    class_id: Optional[int]
    stream_id: Optional[int]

    class Config:
        from_attributes = True