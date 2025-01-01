
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
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    remarks: Optional[str]

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