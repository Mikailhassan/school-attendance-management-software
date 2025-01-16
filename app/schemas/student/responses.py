# schemas/student/responses.py
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional, List, Dict
from ..user.base import UserBase

class StudentBaseResponse(BaseModel):
    id: int
    name: str
    admission_number: str
    class_id: int
    stream_id: Optional[int]
    school_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        
        
class StudentResponse(BaseModel):
    id: int
    name: str
    admission_number: str
    class_id: int
    stream_id: Optional[int]
    school_id: int
    date_of_birth: date
   
    
    # Include basic parent info
    parent_name: str
    parent_phone: str
    parent_email: EmailStr

    class Config:
        from_attributes = True
        
        
        
class PaginatedStudentResponse(BaseModel):
    items: List[StudentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True        
        
class StudentCreateResponse(StudentBaseResponse):
    created_at: datetime
    updated_at: Optional[datetime] = None

class StudentDetailResponse(StudentBaseResponse):
    pass

class StudentUpdateResponse(StudentBaseResponse):
    updated_at: datetime

class StudentListResponse(BaseModel):
    students: List[StudentBaseResponse]
    total_count: int

    class Config:
        from_attributes = True

class AttendanceSummary(BaseModel):
    total_days: int
    present_days: int
    absent_days: int
    attendance_percentage: float
    monthly_summary: Dict[str, float]
    latest_attendance: Optional[datetime] = None

    class Config:
        from_attributes = True

class StudentDetailResponse(StudentBaseResponse):
    form: str
    stream: Optional[str] = None
    attendance_records: List[dict] = []  # List of attendance records
    attendance_summary: AttendanceSummary
    parent_info: Optional[dict] = None   # Basic parent information if available
    
    class Config:
        from_attributes = True

class StudentAttendanceSummary(BaseModel):
    student_id: int
    student_name: str
    admission_number: str
    form: str
    stream: Optional[str] = None
    summary: AttendanceSummary
    term_attendance: Dict[str, float] = {}  # Term-wise attendance percentage
    recent_absences: List[date] = []        # Recent absence dates
    
    class Config:
        from_attributes = True