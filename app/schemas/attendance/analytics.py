from pydantic import BaseModel
from typing import Dict, Any, Optional

class AttendanceAnalytics(BaseModel):
    teacher_info: Dict[str, Any]
    student_info: Dict[str, Any]
    parent_info: Dict[str, Any]
    weekly_analysis: Optional[Dict[str, Any]]
    monthly_analysis: Optional[Dict[str, Any]]
    term_analysis: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
