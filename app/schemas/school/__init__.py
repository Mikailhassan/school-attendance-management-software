# app/schemas/school/__init__.py
from .base import SchoolBase, StreamBase
from .requests import (
    SchoolCreateRequest,
    SchoolUpdateRequest,
    StreamCreateRequest,
    SchoolRegistrationRequest,
    SessionCreateRequest,
    SessionUpdateRequest,
    ClassCreateRequest,
    ClassUpdateRequest,
    StreamUpdateRequest,
    SchoolType,
    SchoolAdminRegistrationRequest
)
from .responses import (
    SchoolResponse,
    StreamResponse,
    SchoolDetailResponse,
    SessionResponse,
    ClassResponse
)

__all__ = [
    'SchoolBase',
    'StreamBase',
    'SchoolCreateRequest',
    'SchoolUpdateRequest',
    'StreamCreateRequest',
    'SchoolRegistrationRequest',
    'SessionCreateRequest',
    'SessionUpdateRequest',
    'ClassCreateRequest',
    'ClassUpdateRequest',
    'StreamUpdateRequest',
    'SchoolType',
    'SchoolResponse',
    'StreamResponse',
    'SchoolDetailResponse',
    'SessionResponse',
    'ClassResponse'
]