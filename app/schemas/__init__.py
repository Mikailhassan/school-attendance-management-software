# Import enums
from .enums import UserRole

# Import authentication-related schemas
from .auth.tokens import (
    Token, 
    TokenData, 
    TokenRefreshRequest, 
    TokenRefreshResponse, 
    RevokedTokenResponse
)
from .auth.requests import (
    RegisterRequest, 
    LoginRequest, 
    PasswordResetRequest, 
    PasswordChange
)

# Import user-related schemas
from .user.base import UserBase
from .user.requests import (
    UserCreate,
    RegisterRequest,
    UserUpdate,
    LoginRequest,
    PasswordChange,
    PasswordResetRequest,
    UserUpdateRequest
)

from .user.responses import (
    UserProfileResponse, 
    UserResponse, 
   
    RegisterResponse,
    LoginResponse
)

# Import teacher-related schemas
from .teacher.base import (
    TeacherBase, 
   
)
from .teacher.requests import (
     TeacherCreate, 
    TeacherUpdate, 
    TeacherRegistrationRequest
)
from .teacher.responses import TeacherResponse

# Import student-related schemas
from .student.base import (
    StudentBase, 
    
)
from .student.requests import (
    StudentCreate, 
    StudentUpdate, 
    StudentRegistrationRequest
)
from .student.responses import (
    StudentResponse
)

# Import parent-related schemas
# from .parent.base import (
#     ParentBase, 
#     ParentCreate, 
#     ParentResponse, 
#     ParentUpdate
# )

# Import school-related schemas
from .school.base import (
    SchoolBase, 
    StreamBase, 
)   
from .school.requests import (
    SchoolCreate, 
    School, 
    SchoolUpdate, 
    StreamCreate
)
from .school.responses import (
    StreamResponse
)


# Import attendance-related schemas
from .attendance.base import (
    AttendanceBase, 
   
)
from .attendance.requests import (
    AttendanceCreate, 
    AttendanceRequest
    
)
from .attendance.responses import (
    AttendanceResponse,
    WeeklyAttendanceResponse, 
    PeriodAttendanceResponse, 
    Attendance
    
)

from .attendance.analytics import AttendanceAnalytics

from app.schemas.user.role import (
    UserRoleEnum,
    RoleDetails,
    RegisterResponse
)
# Import common schemas
from .common.pagination import Page
from .common.error import ErrorResponse


# Export all imported schemas
__all__ = [
    # Enums
    'UserRole',
    
    # Authentication Schemas
    'Token', 'RegisterResponse', 'LoginResponse', 'TokenData', 
    'TokenRefreshRequest', 'TokenRefreshResponse', 'RevokedTokenResponse',
    'RegisterRequest', 'LoginRequest', 'PasswordResetRequest', 'PasswordChange',
    
    # User Schemas
    'UserBase', 'UserCreate', 'UserUpdate', 'UserProfileResponse', 
    'UserResponse', 'UserUpdateRequest',
    
    # Teacher Schemas
    'TeacherBase', 'TeacherCreate', 'TeacherResponse', 'TeacherUpdate', 
    'TeacherRegistrationRequest',
    
    # Student Schemas
    'StudentBase', 'StudentCreate', 'StudentResponse', 'StudentUpdate', 
    'StudentRegistrationRequest',
    
    # Parent Schemas
    'ParentBase', 'ParentCreate', 'ParentResponse', 'ParentUpdate',
    
    # School Schemas
    'SchoolBase', 'SchoolCreate', 'School', 'SchoolUpdate', 
    'StreamBase', 'StreamCreate', 'StreamResponse',
    
    # Attendance Schemas
    'AttendanceBase', 'AttendanceCreate', 'Attendance', 'AttendanceRequest', 
    'AttendanceResponse', 'WeeklyAttendanceResponse', 'PeriodAttendanceResponse', 
    'AttendanceAnalytics',
    
    # Common Schemas
    'Page', 'ErrorResponse',
    
    # Fingerprint Schemas
    'FingerprintBase', 'FingerprintCreate', 'FingerprintResponse'
]