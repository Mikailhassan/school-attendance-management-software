from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete, func
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError  
from passlib.context import CryptContext
from app.services.session_manager import SessionManager
from app.core.config import settings
from app.core.redis import get_redis, SESSION_TTL
import uuid
import re
import asyncio
from app.core.database import get_db
from pydantic_settings import BaseSettings
from pydantic import validator, field_validator
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
    SECRET_KEY: str = settings.SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_ISSUER: str = "school_attendance_system"
    TOKEN_AUDIENCE: str = "yoventa"
    SESSION_EXPIRE_MINUTES: int = 60
    
    # Security settings
    FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    RATE_LIMIT_MAX_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 300
    
    # Cookie settings
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_PATH: str = "/"
    
    # Optional: Add type hints for common JWT claims
    REQUIRED_CLAIMS: list = ["exp", "iat", "sub", "type", "aud", "iss"]
    OPTIONAL_CLAIMS: list = ["email", "role", "school_id", "user_id", "device_info"]

    class Config:
        env_prefix = "JWT_"
        case_sensitive = True

    @field_validator("TOKEN_ISSUER", "TOKEN_AUDIENCE", mode="before")
    @classmethod
    def validate_token_settings(cls, v, info):
        if not v:
            if info.field_name == "TOKEN_ISSUER":
                return "school_attendance_system"
            if info.field_name == "TOKEN_AUDIENCE":
                return "yoventa"
        return v

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def validate_samesite(cls, v):
        allowed_values = ["lax", "strict", "none"]
        if v.lower() not in allowed_values:
            raise ValueError(f"COOKIE_SAMESITE must be one of {allowed_values}")
        return v.lower()

     
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
        
        # Single source of truth for settings
        self._lockout_duration_minutes = self.settings.LOCKOUT_DURATION_MINUTES
        self._max_login_attempts = self.settings.FAILED_LOGIN_ATTEMPTS
        self._session_expire_minutes = self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
        
        # Initialize storage with proper typing
        self.token_blacklist: Set[str] = set()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.login_attempts: Dict[str, Dict[str, Any]] = {}
        
        # Initialize locks
        self.session_lock = asyncio.Lock()
        self.rate_limit_lock = asyncio.Lock()



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

    async def check_rate_limit(self, email: str, ip: str) -> None:
        """Check rate limit and account lockout"""
        async with self.rate_limit_lock:
            key = f"{email}:{ip}"
            attempts = self.login_attempts.get(key, {"count": 0, "timestamp": None})
            
            if attempts["count"] >= self._max_login_attempts:  # Fixed: Using _max_login_attempts
                if attempts["timestamp"]:
                    lockout_time = attempts["timestamp"] + timedelta(minutes=self._lockout_duration_minutes)
                    if datetime.now(timezone.utc) < lockout_time:
                        time_remaining = (lockout_time - datetime.now(timezone.utc)).seconds // 60
                        logger.warning(
                            "Account locked out",
                            extra={
                                "email": email,
                                "ip": ip,
                                "minutes_remaining": time_remaining
                            }
                        )
                        raise AccountLockedException(
                            f"Account locked. Try again in {time_remaining} minutes."
                        )
                    else:
                        # Reset attempts if lockout period has passed
                        self.login_attempts[key] = {"count": 0, "timestamp": None}
                        logger.info(
                            "Lockout period expired, attempts reset",
                            extra={
                                "email": email,
                                "ip": ip
                            }
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
        # Get base settings
        base_settings = self.get_cookie_settings(request)
        
        # Access token settings - available at root path
        access_settings = {
            **base_settings,
            "path": "/",  # Root path for access token
        }
        
        # Refresh token settings - only available at refresh endpoint
        refresh_settings = {
            **base_settings,
            "path": "/api/v1/auth/refresh-token",  # Restrict to refresh endpoint
        }
        
        # Set access token
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            max_age=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            **access_settings
        )
        
        # Set refresh token with restricted path
        response.set_cookie(
            key="refresh_token",
            value=f"Bearer {refresh_token}",
            max_age=self.settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            **refresh_settings
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

    async def record_failed_attempt(self, email: str, ip: str) -> None:
        """Record failed login attempt"""
        async with self.rate_limit_lock:
            key = f"{email}:{ip}"
            attempts = self.login_attempts.get(key, {"count": 0, "timestamp": None})
            attempts["count"] += 1
            attempts["timestamp"] = datetime.now(timezone.utc)
            self.login_attempts[key] = attempts
            
            logger.warning(
                "Failed login attempt recorded",
                extra={
                    "email": email,
                    "ip": ip,
                    "attempt_count": attempts["count"],
                    "max_attempts": self._max_login_attempts  
                }
            )

    async def clear_failed_attempts(self, email: str, ip: str) -> None:
        """Clear failed login attempts after successful login"""
        async with self.rate_limit_lock:
            key = f"{email}:{ip}"
            if key in self.login_attempts:
                del self.login_attempts[key]
                logger.info(
                    "Cleared failed login attempts",
                    extra={
                        "email": email,
                        "ip": ip
                    }
                )
                    
    async def create_token(
            self,
            data: Dict[str, Any],
            token_type: str = "access"
        ) -> str:
        """Create a new token with session management"""
        try:
            if not data.get('sub'):
                raise ValueError("Missing required 'sub' claim in token data")
                
            to_encode = data.copy()
            current_time = datetime.now(timezone.utc)
            
            # Set expiration based on token type
            if token_type == "access":
                expire = current_time + timedelta(minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                try:
                    session_id = await self.create_session(str(data['sub']), data)
                    to_encode['session_id'] = session_id
                    to_encode['jti'] = session_id
                except Exception as e:
                    logger.error("Session creation failed", exc_info=True)
                    raise AuthenticationError(
                        message="Failed to create session",
                        error_code="SESSION_ERROR"
                    )
            else:
                expire = current_time + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS)
                to_encode['jti'] = str(uuid.uuid4())
            
            # Add standard claims including issuer
            to_encode.update({
                "exp": expire,
                "iat": current_time,
                "type": token_type,
                "iss": self.settings.TOKEN_ISSUER,  # Add issuer claim
                "aud": self.settings.TOKEN_AUDIENCE
            })
            
            token = jwt.encode(
                to_encode,
                self.settings.SECRET_KEY,
                algorithm=self.settings.ALGORITHM
            )
            
            logger.debug(
                "Token created successfully",
                extra={
                    "user_id": data.get('sub'),
                    "token_type": token_type,
                    "expires": expire.isoformat(),
                    "issuer": self.settings.TOKEN_ISSUER,  # Log issuer for debugging
                    "session_id": to_encode.get('session_id', None)
                }
            )
            
            return f"Bearer {token}"
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(
                "Token creation failed",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "user_id": data.get('sub'),
                    "token_type": token_type
                }
            )
            raise AuthenticationError(
                message="Failed to create token",
                error_code="TOKEN_CREATION_ERROR"
            )

    async def verify_token(self, token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
        """Verify and decode a JWT token with session validation"""
        session_manager = None
        try:
            # Clean token input
            if token.startswith("Bearer "):
                token = token[7:]
            
            try:
                jwt.get_unverified_header(token)
            except JWTError:
                logger.warning("Invalid token structure")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
            
            try:
                payload = jwt.decode(
                    token,
                    self.settings.SECRET_KEY,
                    algorithms=[self.settings.ALGORITHM],
                    audience=self.settings.TOKEN_AUDIENCE,
                    issuer=self.settings.TOKEN_ISSUER
                )
            except jwt.InvalidIssuerError:
                logger.warning(
                    "Token issuer validation failed",
                    extra={"expected_issuer": self.settings.TOKEN_ISSUER}
                )
                raise JWTError("Invalid token issuer")
            except jwt.InvalidAudienceError:
                logger.warning(
                    "Token audience validation failed",
                    extra={"expected_audience": self.settings.TOKEN_AUDIENCE}
                )
                raise JWTError("Invalid token audience")
            except jwt.ExpiredSignatureError:
                logger.warning("Token has expired")
                raise JWTError("Token has expired")
            except JWTError as e:
                logger.warning(f"Token validation failed: {str(e)}")
                raise
            
            # Validate token claims
            self._validate_token_claims(payload, expected_type)
            
            # Check token revocation before session validation
            jti = payload.get('jti')
            if jti:
                try:
                    is_revoked = await self.check_token_revocation(jti)
                    if is_revoked:
                        logger.warning(f"Token {jti} has been revoked")
                        raise JWTError("Token has been revoked")
                except AttributeError as e:
                    logger.error(f"Token revocation check failed: {str(e)}", exc_info=True)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Unable to verify token status"
                    )
            
            # Session validation for access tokens
            if payload.get("type") == "access":
                session_id = payload.get("session_id")
                if not session_id:
                    logger.warning("Missing session ID in access token")
                    raise JWTError("Invalid token: missing session")
                    
                session_manager = SessionManager()
                await session_manager.initialize()
                
                session = await session_manager._validate_session(session_id)
                if not session:
                    raise JWTError("Invalid token: session expired")
            
            return payload
            
        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            logger.error("Unexpected error during token verification", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        finally:
            if session_manager:
                await session_manager.close()
    def _validate_token_claims(self, payload: Dict[str, Any], expected_type: Optional[str]) -> None:
        """Separate method for token claims validation"""
        if not payload.get("sub"):
            raise JWTError("Missing user identifier")
        
        if not payload.get("type"):
            raise JWTError("Missing token type")
        
        if expected_type and payload["type"] != expected_type:
            raise JWTError(f"Invalid token type")
        
        if payload.get("iss") != self.settings.TOKEN_ISSUER:
            raise JWTError("Invalid token issuer")
            
        if payload.get("aud") != self.settings.TOKEN_AUDIENCE:
            raise JWTError("Invalid token audience")

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

    async def check_token_revocation(self, jti: str) -> bool:
        """
        Check if a token has been revoked
        
        Args:
            jti: The JWT ID to check
            
        Returns:
            bool: True if token is revoked, False otherwise
        """
        try:
            # Create the select statement
            query = select(RevokedToken).where(RevokedToken.jti == jti)
            
            # Since self.db is already an AsyncSession, we can use it directly
            async with self.db.begin() as transaction:
                # Execute query using the session
                result = await self.db.execute(query)
                revoked_token = result.scalar_one_or_none()
                
                is_revoked = revoked_token is not None
                
                if is_revoked:
                    logger.info(f"Token {jti} found in revocation list")
                
                return is_revoked
                    
        except Exception as e:
            logger.error(
                "Failed to check token revocation status",
                extra={
                    "jti": jti,
                    "error": str(e)
                },
                exc_info=True
            )
            # Fail open - treat any errors as non-revoked
            # Change this to True if you want to fail secure
            return False
    async def authenticate_user(
        self,
        email: str,
        password: str,
        response: Response,
        request: Request,
        language: str = 'en'
    ) -> LoginResponse:
        """Authenticate user and generate tokens with proper error handling and logging"""
        try:
            client_ip = request.client.host if request.client else "unknown"
            
            # Check rate limit and account lockout
            await self.check_rate_limit(email, client_ip)  
            await self.check_account_lockout(email, language)
            
            # Get user from database directly
            user = await self.get_user_by_email(email)
            if not user:
                await self.record_failed_attempt(email, client_ip)
                logger.warning(f"Login attempt failed: User not found for email {email}")
                raise InvalidCredentialsException(get_error_message("invalid_credentials", language))

            # Verify password - synchronous operation
            if not self.verify_password(password, user.password_hash):
                await self.record_failed_attempt(email, client_ip)
                logger.warning(f"Login attempt failed: Invalid password for user {email}")
                raise InvalidCredentialsException(get_error_message("invalid_credentials", language))

            if not user.is_active:
                logger.warning(f"Login attempt failed: Inactive account for user {email}")
                raise AuthenticationError(get_error_message("account_inactive", language))

            # Clear failed attempts on successful login
            await self.clear_failed_attempts(email, client_ip)

            # Generate token data with comprehensive claims
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "school_id": str(user.school_id) if user.school_id else None,
                "user_id": str(user.id), 
                "device_info": {
                    "ip": client_ip,
                    "user_agent": request.headers.get("user-agent")
                },
                "iss": self.settings.TOKEN_ISSUER,  
            }

            # Generate tokens with logging
            current_time = datetime.now(timezone.utc)
            logger.debug(
                "Generating tokens",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                    "timestamp": current_time.isoformat()
                }
            )

            # Generate tokens
            access_token = await self.create_token(token_data, "access")
            refresh_token = await self.create_token(token_data, "refresh")

            # Calculate and log expiration times
            access_expire = current_time + timedelta(minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            refresh_expire = current_time + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS)

            logger.debug(
                "Token expiration times",
                extra={
                    "access_token_expires": access_expire.isoformat(),
                    "refresh_token_expires": refresh_expire.isoformat()
                }
            )

            # Get cookie settings based on environment
            cookie_settings = self.get_cookie_settings(request)

            # Set access token cookie
            response.set_cookie(
                key="access_token",
                value=access_token,
                max_age=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
                **cookie_settings
            )
            
            # Set refresh token cookie with restricted path
            refresh_cookie_settings = {
                **cookie_settings,
                "path": "/api/v1/auth/refresh-token"  # Restrict refresh token to refresh endpoint
            }
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                max_age=self.settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,  # Convert to seconds
                **refresh_cookie_settings
            )
            
            # Set security headers
            response.headers.update({
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
            })

            # Log successful login
            logger.info(
                "User logged in successfully",
                extra={
                    "user_id": str(user.id),
                    "email": user.email,
                    "ip": client_ip
                    
                }
            )

            return LoginResponse(
                user=UserResponse.from_orm(user).model_dump(),
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Return expiration in seconds
                refresh_expires_in=self.settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
            )

        except (InvalidCredentialsException, AuthenticationError) as e:
            # Re-raise known exceptions
            raise

        except Exception as e:
            # Log unexpected errors
            logger.error(
                "Unexpected error during authentication",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "email": email
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_error_message("login_failed", language)
            )
        
    async def cleanup_expired_data(self) -> None:
        """Cleanup expired tokens and failed login attempts"""
        async with self.db.begin() as transaction:
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
                
                await transaction.commit()
                
            except Exception as e:
                await transaction.rollback()
                logger.error(
                    "Error cleaning up expired data",
                    extra={"error_type": type(e).__name__}
                )

    async def refresh_access_token(
        self,
        refresh_token: str,
        response: Response,
        request: Request,
        language: str = 'en'
    ) -> Dict[str, str]:
        """Refresh access token using refresh token"""
        try:
            # Clean the refresh token
            refresh_token = refresh_token.replace("Bearer ", "").strip()
            
            # Check if refresh token is revoked
            if await self.check_token_revocation(refresh_token):
                raise AuthenticationError("Refresh token has been revoked")

            # Verify refresh token
            payload = await self.verify_token(refresh_token)
            
            if not payload or payload.get("type") != "refresh":
                raise AuthenticationError(
                    get_error_message("invalid_refresh_token", language)
                )
            
            # Verify token expiration with grace period
            exp = payload.get("exp")
            if not exp or datetime.utcnow() > datetime.fromtimestamp(exp + 300):  # 5 min grace period
                raise AuthenticationError("Refresh token has expired")
            
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
            
            # Log successful token refresh
            logger.info(
                "Access token refreshed successfully",
                extra={
                    "user_id": payload.get("sub"),
                    "email": payload.get("email")
                }
            )
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
            
        except (JWTError, AuthenticationError) as e:
            logger.warning(
                f"Token refresh failed: {str(e)}",
                extra={
                    "error": str(e),
                    "refresh_token": refresh_token[:10] + "..."  
                }
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": get_error_message("token_refresh_failed", language),
                    "code": "TOKEN_REFRESH_FAILED"
                }
            )
        except Exception as e:
            logger.error(
                f"Unexpected error during token refresh: {str(e)}",
                extra={"error_type": type(e).__name__}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": get_error_message("token_refresh_failed", language),
                    "code": "INTERNAL_SERVER_ERROR"
                }
            )

    async def logout(
        self,
        token: str,
        response: Response,
        request: Request,
        language: str = 'en'
    ) -> Dict[str, str]:
        """Log out user and end their session"""
        try:
            if token:
                # Get session ID from token
                payload = await self.verify_token(token)
                session_id = payload.get("session_id")
                
                if session_id:
                    await self.end_session(session_id)
                
                # Revoke the token
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
            token: str | None,
            language: str = 'en'
        ) -> Dict[str, Any]:
        """Validate token and return payload"""
        if not token:
            logger.debug("No token provided to validate_token")
            raise AuthenticationError("No token provided")
            
        try:
            # Verify the token
            logger.debug("Attempting to verify token")
            payload = await self.verify_token(token)
            
            # Verify token type is access token
            if payload.get("type") != "access":
                logger.debug(f"Invalid token type: {payload.get('type')}")
                raise AuthenticationError("Invalid token type")
                
            # Validate session
            session_id = payload.get("session_id")
            if session_id:
                session_manager = SessionManager()
                try:
                    await session_manager.initialize()
                    session = await session_manager._validate_session(session_id)
                    if not session:
                        raise AuthenticationError("Invalid or expired session")
                finally:
                    await session_manager.close()
                
            logger.debug("Token validated successfully")
            return payload
            
        except (JWTError, AuthenticationError) as e:
            logger.warning(f"Token validation failed: {str(e)}")
            raise AuthenticationError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            raise AuthenticationError("Token validation failed")

        
        
    async def create_session(self, user_id: str, token_data: Dict[str, Any]) -> str:
        """Create a new session using SessionManager"""
        try:
            session_manager = SessionManager()
            await session_manager.initialize()
            
            try:
                session_id = await session_manager._create_session(user_id, token_data)
                return session_id
            except Exception as e:
                logger.error(
                    "Session creation failed",
                    exc_info=True,
                    extra={
                        "error_type": type(e).__name__,
                        "user_id": user_id
                    }
                )
                raise AuthenticationError("Failed to create session")
            finally:
                await session_manager.close()
                
        except Exception as e:
            logger.error(
                "Session manager initialization failed",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "user_id": user_id
                }
            )
            raise AuthenticationError("Failed to initialize session manager")


    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate a session using SessionManager"""
        try:
            session_manager = SessionManager()
            await session_manager.initialize()
            
            session_data = await session_manager._validate_session(session_id)
            await session_manager.close()
            
            return session_data
            
        except Exception as e:
            logger.error(
                "Session validation failed in AuthService",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "session_id": session_id
                }
            )
            return None

    async def end_session(self, session_id: str) -> None:
        """End a session using SessionManager"""
        try:
            session_manager = SessionManager()
            await session_manager.initialize()
            
            await session_manager._end_session(session_id)
            await session_manager.close()
            
        except Exception as e:
            logger.error(
                "Failed to end session in AuthService",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "session_id": session_id
                }
            )

            
    
            
               
    async def get_token_from_request(self, request: Request) -> str | None:
            """Extract token from request headers or cookies"""
            # Try to get token from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                return auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Try to get token from cookie
            access_token = request.cookies.get("access_token")
            if access_token and access_token.startswith("Bearer "):
                return access_token[7:]
                
            return access_token  # Return None or token without Bearer prefix


        # Dependency for FastAPI
async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService instance"""
    return AuthService(db)


    # Startup event handler for FastAPI
async def start_cleanup_task(app: FastAPI) -> None:
    """Start the cleanup task when the application starts"""
    auth_service = await get_auth_service()
    asyncio.create_task(setup_cleanup_task(auth_service))
            
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
    
    
 