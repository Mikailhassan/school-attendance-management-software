from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List, Optional

# Base schema for common fields
class UserBase(BaseModel):
    name: str
    gender: str
    email: EmailStr
    phone: str
    date_of_birth: date

# Student schemas
class StudentBase(UserBase):
    admission_number: str
    class_name: str
    stream: Optional[str] = None
    date_of_joining: date
    address: Optional[str] = None

class StudentCreate(StudentBase):
    parent_id: int
    school_id: int

class Student(StudentBase):
    id: int

    class Config:
        orm_mode = True  # Enables compatibility with ORM models

# Teacher schemas
class TeacherBase(UserBase):
    tsc_number: str

class TeacherCreate(TeacherBase):
    school_id: int

class Teacher(TeacherBase):
    id: int

    class Config:
        orm_mode = True

# Parent schemas
class ParentBase(UserBase):
    pass  # Extend with parent-specific fields if needed

class ParentCreate(ParentBase):
    pass

class Parent(ParentBase):
    id: int
    children: List[Student] = []

    class Config:
        orm_mode = True

# School schemas
class SchoolBase(BaseModel):
    name: str
    address: Optional[str] = None
    established_date: Optional[date] = None

class SchoolCreate(SchoolBase):
    pass

class School(SchoolBase):
    id: int
    students: List[Student] = []
    teachers: List[Teacher] = []

    class Config:
        orm_mode = True

# Attendance schemas
class AttendanceBase(BaseModel):
    user_id: int
    check_in_time: date
    check_out_time: Optional[date] = None
    is_present: bool = False

class AttendanceCreate(AttendanceBase):
    pass

class Attendance(AttendanceBase):
    id: int

    class Config:
        orm_mode = True

# Fingerprint schemas
class FingerprintBase(BaseModel):
    user_id: int
    fingerprint_data: str

class FingerprintCreate(FingerprintBase):
    pass

class Fingerprint(FingerprintBase):
    id: int

    class Config:
        orm_mode = True
