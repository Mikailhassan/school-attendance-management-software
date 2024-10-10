from .auth_service import (
    AuthService,
    hash_password,
    verify_password
)
from .attendance_service import AttendanceService
from .fingerprint_service import FingerprintService
from .registration_service import RegistrationService

auth_service = AuthService()
