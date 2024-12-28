# app/schemas/teacher/__init__.py
from .base import TeacherBase
from .requests import (
    TeacherCreate,
    TeacherUpdate,
    TeacherRegistrationRequest
)
from .responses import (
    TeacherResponse,
    TeacherUpdateResponse,
    TeacherListResponse
)

__all__ = [
    'TeacherBase',
    'TeacherCreate',
    'TeacherUpdate',
    'TeacherRegistrationRequest',
    'TeacherResponse',
    'TeacherUpdateResponse',
    'TeacherListResponse'
]