from .base import Base, TenantModel
from .school import School
from .class_ import Class
from .stream import Stream
from .teacher_attendance import TeacherAttendance
from .student_attendance import StudentAttendance
from .fingerprint import Fingerprint
from .attendance_base import AttendanceBase
from .user import User, RevokedToken
from .parent import Parent
from .sessions import Session
from .student import Student  # Add this import

__all__ = [
    'Base',
    'TenantModel',
    'School',
    'Class',
    'Stream',
    'TeacherAttendance',
    'StudentAttendance',
    'Fingerprint',
    'AttendanceBase',
    'User',
    'RevokedToken',
    'Parent',
    'Session',
    'Student'  # Add this to __all__
]