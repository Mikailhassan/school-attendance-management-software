from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional

# Base Student Response (common fields for all responses)
class StudentBaseResponse(BaseModel):
    id: int  # Unique ID of the student
    name: str  # Full name of the student
    email: EmailStr  # Email address
    phone: Optional[str] = None  # Optional phone number
    form: str  # Form the student belongs to (e.g., "Form 1")
    stream: Optional[str] = None  # Stream the student belongs to (e.g., "Form 1A")
    date_of_birth: Optional[date] = None  # Optional date of birth
    admission_number: str  # Unique admission number for the student
    profile_picture: Optional[str] = None  # Optional profile picture URL
    school_id: int  # ID of the school the student belongs to

    class Config:
        from_attributes = True

# Response for a newly created student
class StudentCreateResponse(StudentBaseResponse):
    created_at: datetime  # Timestamp when the student was created
    updated_at: Optional[datetime] = None  # Timestamp of last update

# Response for student details (after fetching)
class StudentDetailResponse(StudentBaseResponse):
    pass  # This inherits from StudentBaseResponse to include common fields

# Response for student update (returning updated details)
class StudentUpdateResponse(StudentBaseResponse):
    updated_at: datetime  # Timestamp of when the student was updated

# Response for a list of students (used when fetching multiple students)
class StudentListResponse(BaseModel):
    students: list[StudentBaseResponse]  # List of student objects
    total_count: int  # Total number of students (useful for pagination)

    class Config:
        from_attributes = True
