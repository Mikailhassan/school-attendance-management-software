# app/schemas/attendance/responses.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
from .info import ClassInfo, StreamInfo, StudentInfo, SessionInfo

class StreamAttendanceResponse(BaseModel):
    stream_info: StreamInfo
    students: List[StudentInfo]
    attendance_date: datetime
    session_info: SessionInfo

    class Config:
        from_attributes = True

class ClassAttendanceResponse(BaseModel):
    class_info: ClassInfo
    streams: List[StreamAttendanceResponse]
    attendance_date: datetime
    session_info: SessionInfo

    class Config:
        from_attributes = True

class StudentAttendanceRecord(BaseModel):
    date: datetime
    class_name: str
    stream_name: str
    status: str
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    remarks: Optional[str]

    class Config:
        from_attributes = True

class AttendanceAnalytics(BaseModel):
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_rate: float
    # stream_comparison: Dict[str, float]  # Comparison between streams
    # class_comparison: Dict[str, Dict[str, float]]  # Nested comparison by class and stream
    # trend_data: Dict[str, Any]

    class Config:
        from_attributes = True

class StreamAttendanceSummary(BaseModel):
    stream_info: StreamInfo
    total_sessions: int
    average_attendance_rate: float
    attendance_by_status: Dict[str, int]
    student_records: List[Dict[str, Any]]

    class Config:
        from_attributes = True

class ClassAttendanceSummary(BaseModel):
    class_info: ClassInfo
    streams: List[StreamAttendanceSummary]
    total_sessions: int
    average_attendance_rate: float
    attendance_by_status: Dict[str, int]
    stream_comparison: Dict[str, float]

    class Config:
        from_attributes = True
        
class AttendanceResponse(BaseModel):
    student_id: int
    status: str
    remarks: Optional[str]

    class Config:
        from_attributes = True        
