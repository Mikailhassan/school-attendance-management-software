from .auth_service import AuthService
from .registration_service import RegistrationService
# from .attendance_service import AttendanceService
from .fingerprint_service import FingerprintService
from .school_service import SchoolService
from .email_service import EmailService

from app.core.dependencies import get_current_active_user

__all__ = [
    "AuthService",
    "get_current_active_user",
    "RegistrationService",
    "AttendanceService",
    "FingerprintService",
    "SchoolService",
    "EmailService"
]