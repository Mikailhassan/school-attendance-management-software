from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete, func
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError
from passlib.context import CryptContext
import uuid
import asyncio
from app.core.database import get_db
from pydantic_settings import BaseSettings
from app.models import User, RevokedToken, FailedLoginAttempt
from app.core.errors import (
    ConfigurationError,
    AuthenticationError,
    RateLimitExceeded,
    AccountLockedException,
    InvalidCredentialsException
)
from app.core.logging import logger
from app.schemas import TokenData, UserResponse, LoginResponse
from app.schemas.enums import UserRole
from app.core.errors import get_error_message

class JWTSettings(BaseSettings):
    SECRET_KEY: str = "your-super-secret-key-replace-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    RATE_LIMIT_MAX_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 300
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_PATH: str = "/"

    class Config:
        env_prefix = "JWT_"
     
class SecurityLogging:
    """Secure logging utilities for authentication system"""
    
    @staticmethod
    def sanitize_token(token_or_msg: str) -> str:
        """Remove sensitive JWT data from strings"""
        if not token_or_msg:
            return token_or_msg
        # Remove JWT pattern while preserving structure
        return re.sub(
            r'eyJ[\w-]*\.[\w-]*\.[\w-]*',
            '[REDACTED_TOKEN]',
            str(token_or_msg)
        )

    @staticmethod
    def log_auth_event(
        event_type: str,
        user_id: Optional[str] = None,
        error: Optional[Exception] = None,
        **kwargs
    ) -> None:
        """Standardized auth event logging"""
        log_data = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if user_id:
            log_data["user_id"] = user_id
            
        if error:
            log_data["error_type"] = error.__class__.__name__
            # Sanitize error message
            log_data["error"] = SecurityLogging.sanitize_token(str(error))
            
        # Add any additional kwargs, sanitizing values
        for key, value in kwargs.items():
            if isinstance(value, str):
                log_data[key] = SecurityLogging.sanitize_token(value)
            else:
                log_data[key] = value
                
        if error:
            logger.error("Auth event", extra=log_data)
        else:
            logger.info("Auth event", extra=log_data)        

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = JWTSettings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._rate_limit_cache: Dict[str, List[datetime]] = {}
        self._cache_lock = asyncio.Lock()

    async def get_current_user(self, token: str):
        """Get current user from token"""
        try:
            payload = await self.verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            user = await self.get_user_by_email(payload.get("email"))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return user
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

    @property
    def lockout_duration_minutes(self) -> int:
        return self.settings.LOCKOUT_DURATION_MINUTES

    async def _cleanup_rate_limit_cache(self) -> None:
        """Clean up expired rate limit entries"""
        async with self._cache_lock:
            current_time = datetime.now(timezone.utc)
            window = timedelta(seconds=self.settings.RATE_LIMIT_WINDOW_SECONDS)
            
            for ip in list(self._rate_limit_cache.keys()):
                # Keep only timestamps within the window
                self._rate_limit_cache[ip] = [
                    ts for ts in self._rate_limit_cache[ip]
                    if current_time - ts < window
                ]
                
                # Remove empty entries
                if not self._rate_limit_cache[ip]:
                    del self._rate_limit_cache[ip]

    async def check_rate_limit(self, request: Request) -> None:
        """Check if request exceeds rate limit"""
        ip = request.client.host if request.client else "unknown"
        current_time = datetime.now(timezone.utc)
        
        await self._cleanup_rate_limit_cache()
        
        async with self._cache_lock:
            if ip not in self._rate_limit_cache:
                self._rate_limit_cache[ip] = []
            
            self._rate_limit_cache[ip].append(current_time)
            
            if len(self._rate_limit_cache[ip]) > self.settings.RATE_LIMIT_MAX_REQUESTS:
                raise RateLimitExceeded(
                    "Too many login attempts. Please try again later."
                )

    def get_cookie_settings(self, request: Request) -> Dict[str, Any]:
        """Get secure cookie settings based on environment"""
        host = request.headers.get("host", "").split(":")[0]
        is_localhost = host in ["localhost", "127.0.0.1"]
        
        return {
            "httponly": True,
            "secure": self.settings.COOKIE_SECURE and not is_localhost,
            "samesite": self.settings.COOKIE_SAMESITE,
            "path": self.settings.COOKIE_PATH,
            "domain": None if is_localhost else f".{host}"
        }

    async def set_auth_cookies(
        self,
        response: Response,
        request: Request,
        access_token: str,
        refresh_token: str
    ) -> None:
        """Set secure authentication cookies"""
        cookie_settings = self.get_cookie_settings(request)
        
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            max_age=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            **cookie_settings
        )
        
        response.set_cookie(
            key="refresh_token",
            value=f"Bearer {refresh_token}",
            max_age=self.settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            **cookie_settings
        )

    async def clear_auth_cookies(self, response: Response, request: Request) -> None:
        """Clear authentication cookies"""
        cookie_settings = self.get_cookie_settings(request)
        response.delete_cookie("access_token", **cookie_settings)
        response.delete_cookie("refresh_token", **cookie_settings)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with necessary relationships"""
        try:
            query = (
                select(User)
                .options(
                    selectinload(User.school),
                    selectinload(User.parent_profile),
                    selectinload(User.teacher_profile),
                    selectinload(User.student_profile)
                )
                .where(func.lower(User.email) == email.lower())
            )
            result = await self.db.execute(query)
            return result.unique().scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving user by email: {str(e)}")
            return None

    async def check_account_lockout(self, email: str, language: str = 'en') -> None:
        """Check if account is locked due to failed login attempts"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                minutes=self.settings.LOCKOUT_DURATION_MINUTES
            )
            
            query = (
                select(func.count())
                .select_from(FailedLoginAttempt)
                .where(
                    and_(
                        FailedLoginAttempt.email == email,
                        FailedLoginAttempt.timestamp > cutoff_time
                    )
                )
            )
            
            result = await self.db.execute(query)
            failed_attempts = result.scalar()
            
            if failed_attempts >= self.settings.FAILED_LOGIN_ATTEMPTS:
                error_msg = get_error_message("account_locked", language).format(
                    minutes=self.settings.LOCKOUT_DURATION_MINUTES
                )
                raise AccountLockedException(error_msg)

        except AccountLockedException:
            raise
        except Exception as e:
            logger.error(f"Error checking account lockout: {str(e)}")
            raise AuthenticationError(get_error_message("error_checking_account", language))

    async def record_failed_attempt(self, email: str, request: Request) -> None:
        """Record a failed login attempt"""
        try:
            failed_attempt = FailedLoginAttempt(
                email=email,
                timestamp=datetime.now(timezone.utc),
                ip_address=request.client.host if request.client else None
            )
            self.db.add(failed_attempt)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recording failed attempt: {str(e)}")

    async def clear_failed_attempts(self, email: str) -> None:
        """Clear failed login attempts after successful login"""
        try:
            await self.db.execute(
                delete(FailedLoginAttempt).where(FailedLoginAttempt.email == email)
            )
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error clearing failed attempts: {str(e)}")

    async def create_token(
        self,
        data: Dict[str, Any],
        token_type: str = "access",
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT token"""
        try:
            to_encode = data.copy()
            
            # Convert UserRole enum to string value
            if 'role' in to_encode and isinstance(to_encode['role'], UserRole):
                to_encode['role'] = to_encode['role'].value
            
            # Ensure required fields
            if "sub" not in to_encode and "id" in to_encode:
                to_encode["sub"] = str(to_encode["id"])
            elif "id" not in to_encode and "sub" in to_encode:
                to_encode["id"] = str(to_encode["sub"])
                
            if not to_encode.get("sub"):
                raise ValueError("Token must include user identifier (sub)")
            
            # Set expiration
            if token_type == "access":
                expire = datetime.now(timezone.utc) + (
                    expires_delta if expires_delta
                    else timedelta(minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                )
            else:  # refresh token
                expire = datetime.now(timezone.utc) + timedelta(
                    days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
                )
            
            # Update with standard JWT claims
            to_encode.update({
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "type": token_type,
                "jti": str(uuid.uuid4())
            })
            
            # Log token creation (without sensitive data)
            logger.debug(
                "Creating token",
                extra={
                    "token_type": token_type,
                    "user_id": to_encode.get("sub"),
                    "expiry": expire.isoformat()
                }
            )
            
            return jwt.encode(
                to_encode,
                self.settings.SECRET_KEY,
                algorithm=self.settings.ALGORITHM
            )
        except ValueError as e:
            logger.error(f"Token creation value error: {str(e)}")
            raise AuthenticationError(str(e))
        except Exception as e:
            logger.error(f"Error creating {token_type} token: {str(e)}")
            raise AuthenticationError(f"Could not create {token_type} token")

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            # Clean token
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Decode and verify
            payload = jwt.decode(
                token,
                self.settings.SECRET_KEY,
                algorithms=[self.settings.ALGORITHM]
            )
            
            # Validate required claims
            if not payload.get("sub"):
                raise JWTError("Token missing required 'sub' claim")
            
            if not payload.get("type"):
                raise JWTError("Token missing required 'type' claim")
            
            # Check revocation
            is_revoked = await self.check_token_revocation(token)
            if is_revoked:
                raise JWTError("Token has been revoked")
            
            # Log verification (without sensitive data)
            # Enhanced secure logging for verification
            SecurityLogging.log_auth_event(
            "token_verified",
            user_id=payload.get("sub"),
            token_type=payload.get("type")
            )
            logger.debug(
)
            
            return payload
            
        except jwt.ExpiredSignatureError:
            SecurityLogging.log_auth_event(
                "token_expired",
                user_id=payload.get("sub") if 'payload' in locals() else None,
                token_type=payload.get("type") if 'payload' in locals() else None
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except JWTError as e:
            SecurityLogging.log_auth_event(
                "token_verification_failed",
                error=e
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            SecurityLogging.log_auth_event(
                "token_verification_error",
                error=e
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

    async def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token"""
        try:
            if token.startswith("Bearer "):
                token = token[7:]

            payload = await self.verify_token(token)
            jti = payload.get('jti')
            
            if not jti:
                return False

            revoked_token = RevokedToken(
                jti=jti,
                revoked_at=datetime.now(timezone.utc)
            )
            self.db.add(revoked_token)
            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error revoking token: {str(e)}")
            return False

    async def check_token_revocation(self, token: str) -> bool:
        """Check if token has been revoked"""
        try:
            if token.startswith("Bearer "):
                token = token[7:]
                
            payload = jwt.decode(
                token,
                self.settings.SECRET_KEY,
                algorithms=[self.settings.ALGORITHM]
            )
            jti = payload.get('jti')
            
            if not jti:
                return True
            
            query = (
                select(RevokedToken)
                .where(RevokedToken.jti == jti)
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Token revocation check error: {str(e)}")
            return True

    async def authenticate_user(
        self,
        email: str,
        password: str,
        response: Response,
        request: Request,
        language: str = 'en'
    ) -> LoginResponse:
        """Authenticate user and generate tokens"""
        try:
            # Check rate limit
            await self.check_rate_limit(request)
            
            # Check for account lockout
            await self.check_account_lockout(email, language)
            
            # Get user and verify credentials
            user = await self.get_user_by_email(email)
            
            if not user:
                await self.record_failed_attempt(email, request)
                raise InvalidCredentialsException(
                    get_error_message("invalid_credentials", language)
                )

            if not self.verify_password(password, user.password_hash):
                await self.record_failed_attempt(email, request)
                raise InvalidCredentialsException(
                    get_error_message("invalid_credentials", language)
                )

            if not user.is_active:
                raise AuthenticationError(
                    get_error_message("account_inactive", language)
                )

            # Clear failed attempts on successful login
            await self.clear_failed_attempts(email)

            # Create token data
            token_data = TokenData(
            sub=str(user.id),  
            email=user.email,
            role=user.role, 
            school_id=str(user.school_id) if user.school_id else None,
            user_id=user.id
            )
            logger.debug(f"Token data: {token_data.model_dump()}")

            # Generate tokens
            access_token = await self.create_token(token_data.model_dump(), "access")  # Use model_dump() for v2
            refresh_token = await self.create_token(token_data.model_dump(), "refresh")

            # Set auth cookies
            await self.set_auth_cookies(
                response,
                request,
                access_token,
                refresh_token
            )

            logger.info(f"User authenticated successfully: {email}")

            return LoginResponse(
                user=UserResponse.from_orm(user),
                access_token=access_token,
                refresh_token=refresh_token
            )

        except (RateLimitExceeded, AccountLockedException, 
                InvalidCredentialsException, AuthenticationError) as e:
            logger.warning(f"Authentication failed for {email}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_error_message("authentication_failed", language)
            )



    async def cleanup_expired_data(self) -> None:
        """Cleanup expired tokens and failed login attempts"""
        try:
            cutoff_time = datetime.now(timezone.utc)
            
            # Delete expired revoked tokens
            await self.db.execute(
                delete(RevokedToken).where(
                    RevokedToken.revoked_at < cutoff_time - timedelta(days=30)
                )
            )


        # Delete expired failed login attempts
            await self.db.execute(
                delete(FailedLoginAttempt).where(
                    FailedLoginAttempt.timestamp < 
                    cutoff_time - timedelta(minutes=self.settings.LOCKOUT_DURATION_MINUTES)
                )
            )
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error cleaning up expired data: {str(e)}")

    async def refresh_access_token(
        self,
        refresh_token: str,
        response: Response,
        request: Request,
        language: str = 'en'
    ) -> Dict[str, str]:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = await self.verify_token(refresh_token)
            
            if payload.get("type") != "refresh":
                raise AuthenticationError(
                    get_error_message("invalid_refresh_token", language)
                )
            
            # Create new token data
            token_data = TokenData(
                sub=payload.get("sub"),
                email=payload.get("email"),
                role=payload.get("role"),
                school_id=payload.get("school_id")
            )
            
            # Generate new access token
            new_access_token = await self.create_token(
                token_data.dict(),
                token_type="access"
            )
            
            # Set new access token cookie
            cookie_settings = self.get_cookie_settings(request)
            response.set_cookie(
                key="access_token",
                value=f"Bearer {new_access_token}",
                max_age=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                **cookie_settings
            )
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
            
        except (JWTError, AuthenticationError) as e:
            logger.warning(f"Token refresh failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=get_error_message("token_refresh_failed", language),
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_error_message("token_refresh_failed", language)
            )

    async def logout(
        self,
        token: str,
        response: Response,
        request: Request,
        language: str = 'en'
    ) -> Dict[str, str]:
        """Log out user by revoking their tokens and clearing cookies"""
        try:
            # Revoke the token
            if token:
                await self.revoke_token(token)
            
            # Clear auth cookies
            await self.clear_auth_cookies(response, request)
            
            return {"message": get_error_message("logout_successful", language)}
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_error_message("logout_failed", language)
            )

    async def validate_token(
        self,
        token: str,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """Validate token and return payload"""
        try:
            payload = await self.verify_token(token)
            return payload
        except (JWTError, AuthenticationError) as e:
            logger.warning(f"Token validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=get_error_message("invalid_token", language),
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_error_message("token_validation_failed", language)
            )

    # Background task setup for periodic cleanup
    # Background task setup for periodic cleanup
async def setup_cleanup_task(auth_service: AuthService) -> None:
    """Setup periodic cleanup task"""
    while True:
        try:
            await auth_service.cleanup_expired_data()
            # Run cleanup every hour
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            await asyncio.sleep(60)  # Wait a minute before retrying

# Dependency for FastAPI
async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService instance"""
    return AuthService(db)

# Startup event handler for FastAPI
async def start_cleanup_task(app: FastAPI) -> None:
    """Start the cleanup task when the application starts"""
    auth_service = await get_auth_service()
    asyncio.create_task(setup_cleanup_task(auth_service))
           
            
