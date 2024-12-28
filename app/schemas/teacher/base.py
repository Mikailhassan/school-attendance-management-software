# app/schemas/teacher/base.py
from pydantic import BaseModel, validator
from datetime import date
from ..user.base import UserBase

class TeacherBase(UserBase):
    tsc_number: str
    gender: str
    date_of_joining: date

    @validator('gender')
    def validate_gender(cls, v):
        if v not in ('Male', 'Female', 'Other'):
            raise ValueError('Gender must be either Male, Female, or Other')
        return v

    @validator('tsc_number')
    def validate_tsc_number(cls, v):
        if len(v) < 1:
            raise ValueError('TSC number must not be empty')
        return v

    class Config:
        from_attributes = True
