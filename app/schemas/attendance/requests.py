
# app/schemas/attendance/requests.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class AttendanceRequest(BaseModel):
    student_id: int
    session_id: int
    school_id: int
    class_id: int
    stream_id: int
    status: str
    remarks: Optional[str]

class AttendanceCreate(BaseModel):
    admission_number : int
    session_id: int
    school_id: int
    class_id: int
    stream_id: int
    status: str
    remarks: Optional[str]
    
    class config:
        orm_mode = True

class StreamAttendanceRequest(BaseModel):
    stream_id: int
    class_id: int
    session_id: int
    school_id: int
    attendance_data: List[AttendanceRequest]

class BulkAttendanceRequest(BaseModel):
    session_id: int
    school_id: int
    class_id: int
    stream_ids: List[int]  # Allow marking attendance for multiple streams
    attendance_data: List[AttendanceRequest]