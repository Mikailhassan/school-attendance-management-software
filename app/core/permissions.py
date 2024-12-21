# app/core/permissions.py
from typing import List
from fastapi import HTTPException, status
from app.schemas.user.role import UserRoleEnum
from app.models.user import User

class RoleChecker:
    def __init__(self, allowed_roles: List[UserRoleEnum]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User):  
        if UserRoleEnum(current_user.role) not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return current_user



    def has_role(self, roles: List[str], match_type: str = 'exact') -> bool:
        """
        Advanced role checking with different matching strategies.
        
        :param roles: List of roles to check.
        :param match_type: Matching strategy ('exact', 'prefix', 'regex').
        :return: Boolean indicating role match.
        """
        if not self.user:
            return False

        if match_type == 'exact':
            return any(role in self.user.roles for role in roles)
        elif match_type == 'prefix':
            return any(role.startswith(r) for r in roles for role in self.user.roles)
        elif match_type == 'regex':
            return any(re.match(r, role) for r in roles for role in self.user.roles)
        
        raise ValueError("Invalid match type")

    def require_role(self, roles: List[str], match_type: str = 'exact'):
        """
        Ensures that the user has one of the required roles.
        Raises an HTTPException if not.
        
        :param roles: A list of roles to check.
        :param match_type: Matching strategy for role checking.
        :raises HTTPException: If the user doesn't have one of the required roles.
        """
        if not self.has_role(roles, match_type):
            logger.warning(f"Permission denied: User {self.user.id} lacks required roles")
            raise HTTPException(status_code=403, detail="Permission denied: insufficient role")

    def __call__(self, user: User):
        """
        This makes RoleChecker callable, allowing it to be used as a FastAPI dependency.
        """
        self.user = user
        return self