# app/schemas/attendance/__init__.py
from .base import AttendanceBase
from .requests import (
    AttendanceRequest,
    StreamAttendanceRequest,
    BulkAttendanceRequest
)
from .info import (
    ClassInfo,
    StreamInfo,
    StudentInfo,
    SessionInfo
)
from .responses import (
    StreamAttendanceResponse,
    ClassAttendanceResponse,
    StudentAttendanceRecord,
    AttendanceAnalytics,
    StreamAttendanceSummary,
    ClassAttendanceSummary
)

__all__ = [
    'AttendanceBase',
    'AttendanceRequest',
    'StreamAttendanceRequest',
    'BulkAttendanceRequest',
    'ClassInfo',
    'StreamInfo',
    'StudentInfo',
    'SessionInfo',
    'StreamAttendanceResponse',
    'ClassAttendanceResponse',
    'StudentAttendanceRecord',
    'AttendanceAnalytics',
    'StreamAttendanceSummary',
    'ClassAttendanceSummary'
]