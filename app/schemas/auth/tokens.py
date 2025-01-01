from pydantic import BaseModel
from typing import Optional
from ..enums import UserRole  # Assuming UserRole is defined in enums

# Token model that includes the access token and token type (usually "bearer")
class Token(BaseModel):
    access_token: str  # The JWT access token
    token_type: str = "bearer"  # The token type, defaulting to "bearer"

# Token Data model that contains user-related information embedded in the token
class TokenData(BaseModel):
    sub: str  # Required for JWT standard claims
    email: str
    role: UserRole
    school_id: Optional[str] = None
    user_id: Optional[int] = None

# Token Refresh Request, to send the refresh token to refresh the session
class TokenRefreshRequest(BaseModel):
    refresh_token: str  # Refresh token to request a new access token

# Token Refresh Response, which includes the new access token
class TokenRefreshResponse(BaseModel):
    access_token: str  # The new JWT access token
    token_type: str = "bearer"  # The type of token, defaulting to "bearer"

# Response for a revoked token to indicate whether the token has been revoked or not
class RevokedTokenResponse(BaseModel):
    revoked: bool  # Whether the token has been successfully revoked

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
