from typing import List, Set, Optional, Pattern
from fastapi import HTTPException, status
import re
import logging
from enum import Enum
from app.schemas.user.role import UserRoleEnum
from app.models.user import User

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
        subordinates = cls.HIERARCHY.get(role, set()).copy()
        for sub_role in cls.HIERARCHY.get(role, set()).copy():
            subordinates.update(cls.get_subordinate_roles(sub_role))
        return subordinates

    @classmethod
    def has_permission(cls, user_role: UserRoleEnum, required_role: UserRoleEnum) -> bool:
        """Check if user_role has permission over required_role"""
        if user_role == required_role:
            return True
        return required_role in cls.get_subordinate_roles(user_role)

class RoleChecker:
    """Enhanced role checking with multiple matching strategies and caching"""
    
    def __init__(self, allowed_roles: List[UserRoleEnum]):
        self.allowed_roles = set(allowed_roles)
        self.user: Optional[User] = None
        self._regex_cache: dict[str, Pattern] = {}

    async def __call__(self, current_user: User) -> User:
        """Makes RoleChecker callable for use as a FastAPI dependency"""
        self.user = current_user
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
        """Internal method to check user permissions"""
        user_role = UserRoleEnum(user.role)
        return any(
            RoleHierarchy.has_permission(user_role, required_role)
            for required_role in self.allowed_roles
        )

    def has_role(
        self,
        roles: List[str],
        match_type: MatchType = MatchType.EXACT
    ) -> bool:
        """
        Check if user has any of the specified roles using the specified matching strategy
        
        Args:
            roles: List of roles to check
            match_type: Matching strategy to use
            
        Returns:
            bool: Whether user has matching role
        """
        if not self.user:
            return False

        user_role = self.user.role
        
        if match_type == MatchType.EXACT:
            return user_role in roles
            
        elif match_type == MatchType.PREFIX:
            return any(user_role.startswith(role) for role in roles)
            
        elif match_type == MatchType.REGEX:
            return any(self._check_regex(role, user_role) for role in roles)
            
        elif match_type == MatchType.HIERARCHY:
            user_enum_role = UserRoleEnum(user_role)
            return any(
                RoleHierarchy.has_permission(user_enum_role, UserRoleEnum(role))
                for role in roles
            )
            
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

    def require_role(
        self,
        roles: List[str],
        match_type: MatchType = MatchType.EXACT,
        error_message: Optional[str] = None
    ) -> None:
        """
        Ensure user has required role(s)
        
        Args:
            roles: List of required roles
            match_type: Role matching strategy
            error_message: Custom error message
            
        Raises:
            HTTPException: If user lacks required role
        """
        if not self.has_role(roles, match_type):
            message = error_message or f"Permission denied: Role(s) {roles} required"
            logger.warning(
                f"Permission denied: User {self.user.id} lacks required roles. "
                f"User role: {self.user.role}, Required: {roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=message
            )

# Helper functions for common role checks
def require_super_admin():
    return RoleChecker([UserRoleEnum.SUPER_ADMIN])

def require_school_admin():
    return RoleChecker([UserRoleEnum.SUPER_ADMIN, UserRoleEnum.SCHOOL_ADMIN])

def require_teacher():
    return RoleChecker([UserRoleEnum.SUPER_ADMIN, UserRoleEnum.SCHOOL_ADMIN, UserRoleEnum.TEACHER])

def allow_own_school():
    """Custom checker that allows access to users from the same school"""
    allowed_roles = [
        UserRoleEnum.SUPER_ADMIN,
        UserRoleEnum.SCHOOL_ADMIN,
        UserRoleEnum.TEACHER
    ]
    return RoleChecker(allowed_roles)