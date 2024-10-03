from .auth_service import (
    login_user,
    logout_user,
    get_current_admin,
    hash_password,
    verify_password
)
from .attendance_service import AttendanceService
from .fingerprint_service import FingerprintService
from .registration_service import RegistrationService

# We no longer need to import individual registration functions
# as they are now methods of the RegistrationService class