# app/schemas/__init__.py

# Import enums
from .enums import UserRole

# Import common schemas
from .common.pagination import Page
from .common.error import ErrorResponse

# Import auth schemas
from .auth.tokens import (
    Token, 
    TokenData, 
    TokenRefreshRequest, 
    TokenRefreshResponse,
    TokenResponse

)
from .auth.requests import (
    LoginRequest,
    RegisterRequest, 
    PasswordResetRequest, 
    PasswordChange
)
from .auth.responses import (
    LoginResponse,
    RegisterResponse,
)

# Import user schemas
from .user.base import UserBase,UserBaseSchema
from .user.requests import (
    UserCreate,
    UserUpdate,
    UserUpdateRequest,
    SchoolAdminRegistrationRequest,  # Added
    SuperAdminRegistrationRequest    # Added
)
from .user.responses import (
    UserResponse,
    UserProfileResponse,
    UserUpdateResponse
)
from .user.role import (
    UserRoleEnum,
    RoleDetails
)

# Import teacher schemas
from .teacher.base import TeacherBase
from .teacher.requests import (
    TeacherCreate,
    TeacherUpdate,
    TeacherRegistrationRequest,
    TeacherUpdateRequest
)
from .teacher.responses import (
    TeacherResponse,
    TeacherUpdateResponse,
    TeacherListResponse,
    TeacherDetailResponse
)

# Import student schemas
from .student.base import StudentBase
from .student.requests import (
    StudentCreate,
    StudentUpdate,
    StudentRegistrationRequest
)
from .student.responses import (
    StudentBaseResponse,
    StudentCreateResponse,
    StudentDetailResponse,
    StudentUpdateResponse,
    StudentListResponse
)

# Import school schemas
from .school.base import (
    SchoolBase,
    StreamBase
)
from .school.requests import (
    SchoolCreateRequest,
    SchoolUpdateRequest,
    SchoolRegistrationRequest,   # Added
    ClassCreateRequest,
    ClassUpdateRequest,
    StreamCreateRequest,
    StreamUpdateRequest,
    SessionCreateRequest,
    SchoolAdminRegistrationRequest
   
)
from .school.responses import (
    SchoolResponse,
    StreamResponse,
    SessionResponse
   
)

# Import parent schemas
from .parents.requests import ParentRegistrationRequest, ParentCreate, ParentUpdate
from .parents.responses import ParentResponse, ParentCreateResponse, ParentUpdateResponse, ParentListResponse, ParentDetailResponse

# Import attendance schemas
from .attendance.base import AttendanceBase
from .attendance.requests import (
    AttendanceRequest,
    StreamAttendanceRequest,
    BulkAttendanceRequest,
)
from .attendance.responses import (
    
    StreamAttendanceResponse,
    ClassAttendanceResponse,
    StudentAttendanceRecord,
    StreamAttendanceSummary,
    ClassAttendanceSummary,
    AttendanceAnalytics
)
from .attendance.analytics import AttendanceAnalytics

# Export all schemas
__all__ = [
    # Enums
    'UserRole',
    'UserRoleEnum',
    
    # Common schemas
    'Page',
    'ErrorResponse',
    
    # Auth schemas
    'Token',
    'TokenData',
    'TokenRefreshRequest',
    'TokenRefreshResponse',
    'LoginRequest',
    'RegisterRequest',
    'PasswordResetRequest',
    'PasswordChange',
    'LoginResponse',
    'RegisterResponse',
    
    # User schemas
    'UserBase',
    'UserCreate',
    'UserUpdate',
    'UserUpdateRequest',
    'UserResponse',
    'UserProfileResponse',
    'UserUpdateResponse',
    'RoleDetails',
    'SchoolAdminRegistrationRequest',    # Added
    'SuperAdminRegistrationRequest',     # Added
    
    # Teacher schemas
    'TeacherBase',
    'TeacherCreate',
    'TeacherUpdate',
    'TeacherRegistrationRequest',
    'TeacherResponse',
    'TeacherUpdateResponse',
    'TeacherListResponse',
    
    # Student schemas
    'StudentBase',
    'StudentCreate',
    'StudentUpdate',
    'StudentRegistrationRequest',
    'StudentBaseResponse',
    'StudentCreateResponse',
    'StudentDetailResponse',
    'StudentUpdateResponse',
    'StudentListResponse',
    
    # School schemas
    'SchoolBase',
    'StreamBase',
    'SchoolCreateRequest',
    'SchoolUpdateRequest',
    'SchoolRegistrationRequest',    # Added
    'StreamCreateRequest',
    'StreamUpdateRequest',
    'SessionCreateRequest',
    'FormCreateRequest',
    'SchoolResponse',
    'StreamResponse',
    'SessionResponse',
    'FormResponse',
    
    # Parent schemas
    'ParentRegistrationRequest',
    'ParentRegistrationResponse',
    'parentResponse',
    'parentUpdateResponse',
    'parentcreate'
    
    # Attendance schemas
    'AttendanceBase',
    'AttendanceCreate',
    'AttendanceRequest',
    'AttendanceResponse',
    'WeeklyAttendanceResponse',
    'PeriodAttendanceResponse',
    'AttendanceAnalytics'
]