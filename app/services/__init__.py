# services/__init__.py

from .auth_service import (
    login_user,
    register_user,
    logout_user,
    get_current_admin,
    hash_password,
    verify_password
)
from .attendance_service import (
    mark_attendance,
    view_attendance_by_date
)
from .fingerprint_service import (
    FingerprintService
)
from .registration_service import (
    register_student,
    register_teacher,
    register_parent
)


