# app/schemas/teacher/__init__.py
from .base import TeacherBase
from .requests import (
    TeacherCreate,
    TeacherUpdate,
    TeacherRegistrationRequest,
    TeacherUpdateRequest
)
from .responses import (
    TeacherResponse,
    TeacherUpdateResponse,
    TeacherListResponse,
    TeacherDetailResponse
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