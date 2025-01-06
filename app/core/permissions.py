# app/core/permissions.py
from typing import List, Set, Optional, Pattern, Callable
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import re
import logging
from enum import Enum
from functools import wraps
from app.schemas.user.role import UserRoleEnum
from app.models.user import User
from app.core.dependencies import get_current_active_user

logger = logging.getLogger(__name__)

class MatchType(str, Enum):
    EXACT = 'exact'
    PREFIX = 'prefix'
    REGEX = 'regex'
    HIERARCHY = 'hierarchy'

class RoleHierarchy:
    """Define role hierarchy relationships"""
    HIERARCHY = {
        UserRoleEnum.SUPER_ADMIN: {
            UserRoleEnum.SCHOOL_ADMIN,
            UserRoleEnum.TEACHER,
            UserRoleEnum.PARENT,
            UserRoleEnum.STUDENT
        },
        UserRoleEnum.SCHOOL_ADMIN: {
            UserRoleEnum.TEACHER,
            UserRoleEnum.PARENT,
            UserRoleEnum.STUDENT
        },
        UserRoleEnum.TEACHER: {
            UserRoleEnum.STUDENT
        },
        UserRoleEnum.PARENT: set(),
        UserRoleEnum.STUDENT: set()
    }

    @classmethod
    def get_subordinate_roles(cls, role: UserRoleEnum) -> Set[UserRoleEnum]:
        """Get all roles subordinate to the given role"""
        return cls.HIERARCHY.get(role, set())

    @classmethod
    def has_permission(cls, user_role: UserRoleEnum, required_role: UserRoleEnum) -> bool:
        """Check if user_role has permission over required_role"""
        if user_role == required_role:
            return True
        return required_role in cls.get_subordinate_roles(user_role)

class RoleChecker:
    """Enhanced role checking with dependency injection support"""
    
    def __init__(
        self, 
        allowed_roles: List[UserRoleEnum], 
        match_type: MatchType = MatchType.HIERARCHY,
        check_active: bool = True
    ):
        self.allowed_roles = set(allowed_roles)
        self.match_type = match_type
        self.check_active = check_active
        self._regex_cache: dict[str, Pattern] = {}

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Makes RoleChecker callable as a FastAPI dependency"""
        if not self._check_permission(current_user):
            logger.warning(
                f"Permission denied: User {current_user.id} with role {current_user.role} "
                f"attempted to access resource requiring roles {self.allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return current_user

    def _check_permission(self, user: User) -> bool:
        """Check user permissions against allowed roles"""
        try:
            user_role = UserRoleEnum(user.role)
            if self.match_type == MatchType.HIERARCHY:
                return any(
                    RoleHierarchy.has_permission(user_role, required_role)
                    for required_role in self.allowed_roles
                )
            return self.has_role([role.value for role in self.allowed_roles], self.match_type)
        except ValueError:
            logger.error(f"Invalid role value: {user.role}")
            return False

    def has_role(
        self,
        roles: List[str],
        match_type: MatchType = MatchType.EXACT
    ) -> bool:
        """Enhanced role checking with multiple matching strategies"""
        if not hasattr(self, 'user') or not self.user:
            return False

        user_role = self.user.role
        
        match match_type:
            case MatchType.EXACT:
                return user_role in roles
            case MatchType.PREFIX:
                return any(user_role.startswith(role) for role in roles)
            case MatchType.REGEX:
                return any(self._check_regex(role, user_role) for role in roles)
            case MatchType.HIERARCHY:
                user_enum_role = UserRoleEnum(user_role)
                return any(
                    RoleHierarchy.has_permission(user_enum_role, UserRoleEnum(role))
                    for role in roles
                )
            case _:
                raise ValueError(f"Invalid match type: {match_type}")

    def _check_regex(self, pattern: str, role: str) -> bool:
        """Check role against regex pattern with caching"""
        if pattern not in self._regex_cache:
            try:
                self._regex_cache[pattern] = re.compile(pattern)
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                return False
        return bool(self._regex_cache[pattern].match(role))

# Factory functions for common role checks
def require_super_admin():
    return RoleChecker([UserRoleEnum.SUPER_ADMIN])

def require_school_admin():
    return RoleChecker([UserRoleEnum.SUPER_ADMIN, UserRoleEnum.SCHOOL_ADMIN])

def require_teacher():
    return RoleChecker([
        UserRoleEnum.SUPER_ADMIN,
        UserRoleEnum.SCHOOL_ADMIN,
        UserRoleEnum.TEACHER
    ])

def require_parent():
    return RoleChecker([
        UserRoleEnum.SUPER_ADMIN,
        UserRoleEnum.SCHOOL_ADMIN,
        UserRoleEnum.PARENT
    ])

def allow_own_school(check_active: bool = True):
    """Custom checker that allows access to users from the same school"""
    return RoleChecker(
        allowed_roles=[
            UserRoleEnum.SUPER_ADMIN,
            UserRoleEnum.SCHOOL_ADMIN,
            UserRoleEnum.TEACHER
        ],
        check_active=check_active
    )

# Decorator for role-based access control
def require_roles(
    roles: List[UserRoleEnum],
    match_type: MatchType = MatchType.HIERARCHY
):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            checker = RoleChecker(roles, match_type)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            await checker(current_user)
            return await func(*args, **kwargs)
        return wrapper
    return decorator