from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete, func
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError  
from passlib.context import CryptContext
import uuid
import re
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
        self._rate_limit_cache = {}
        
        self.session_lock = asyncio.Lock()
        self.rate_limit_lock = asyncio.Lock()
        
        # Initialize storage
        self.token_blacklist = set()
        self.active_sessions = {}
        self.login_attempts = {}
        
        self._lockout_duration_minutes = getattr(JWTSettings, 'LOCKOUT_DURATION_MINUTES', 15)
        self._max_login_attempts = getattr(JWTSettings, 'MAX_LOGIN_ATTEMPTS', 5)
        
    @property
    def lockout_duration_minutes(self) -> int:
        return self._lockout_duration_minutes

    @property
    def max_login_attempts(self) -> int:
        return self._max_login_attempts



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
            
            if attempts["count"] >= self.max_login_attempts:
                if attempts["timestamp"]:
                    lockout_time = attempts["timestamp"] + timedelta(minutes=self.lockout_duration_minutes)
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
                    "max_attempts": self.max_login_attempts
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
        """Create a new token with improved error handling"""
        try:
            # Validate required data
            if not data.get('sub'):
                raise ValueError("Missing required 'sub' claim in token data")
                
            to_encode = data.copy()
            current_time = datetime.now(timezone.utc)
            
            # Set expiration based on token type
            if token_type == "access":
                expire = current_time + timedelta(minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                # Create session ID for access tokens
                try:
                    session_id = await self._create_session(str(data['sub']), data)
                    to_encode['session_id'] = session_id
                except Exception as e:
                    logger.error("Session creation failed", exc_info=True)
                    raise AuthenticationError(
                        message="Failed to create session",
                        error_code="SESSION_ERROR"
                    )
            else:
                expire = current_time + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS)
            
            # Add standard claims
            to_encode.update({
                "exp": expire,
                "iat": current_time,
                "type": token_type,
                "jti": str(uuid.uuid4())
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
                    "expires": expire.isoformat()
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
        """
        Verify and decode a JWT token, including session validation
        """
        try:
            # Strip 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]
            
            # Decode the token
            payload = jwt.decode(
                token,
                self.settings.SECRET_KEY,
                algorithms=[self.settings.ALGORITHM]
            )
            
            # Basic claim validation
            token_type = payload.get("type")
            if expected_type and token_type != expected_type:
                raise jwt.JWTError(f"Invalid token type: expected {expected_type}")
            
            # Session validation for access tokens
            if token_type == "access":
                session_id = payload.get("session_id")
                if not session_id:
                    logger.warning("Missing session ID in access token", extra={"user_id": payload.get("sub")})
                    raise jwt.JWTError("Invalid token: missing session")
                
                session = await self._validate_session(session_id)
                if not session:
                    logger.warning("Invalid or expired session", extra={"session_id": session_id})
                    raise jwt.JWTError("Invalid token: session expired")
            
            # Check if token has been revoked - using correct attribute name
            if hasattr(self, 'token_blacklist') and token in self.token_blacklist:
                raise jwt.JWTError("Token has been revoked")
            
            logger.debug(
                "Token verified successfully",
                extra={
                    "token_type": token_type,
                    "user_id": payload.get("sub"),
                    "exp": payload.get("exp")
                }
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired", extra={"token_type": expected_type})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
            
        except jwt.JWTError as e:
            logger.warning(f"Invalid token: {str(e)}", extra={"token_type": expected_type})
            if "Signature verification failed" in str(e):
                logger.error("Token signature verification failed - possible invalid secret key or tampered token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        except Exception as e:
            logger.error(
                "Token verification failed",
                extra={"error_type": type(e).__name__},
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
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
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit and account lockout
        await self.check_rate_limit(email, client_ip)  
        await self.check_account_lockout(email, language)
        
        # Get user from database directly
        user = await self.get_user_by_email(email)
        if not user:
            await self.record_failed_attempt(email, request)
            raise InvalidCredentialsException(get_error_message("invalid_credentials", language))

        # Verify password - synchronous operation
        if not self.verify_password(password, user.password_hash):
            await self.record_failed_attempt(email, request)
            raise InvalidCredentialsException(get_error_message("invalid_credentials", language))

        if not user.is_active:
            raise AuthenticationError(get_error_message("account_inactive", language))

        # Clear failed attempts on successful login
        await self.clear_failed_attempts(email, client_ip)

        # Generate token data
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "school_id": str(user.school_id) if user.school_id else None,
            "user_id": user.id,
            "device_info": {
                "ip": client_ip,
                "user_agent": request.headers.get("user-agent")
            }
        }

        # Generate tokens
        access_token = await self.create_token(token_data, "access")
        refresh_token = await self.create_token(token_data, "refresh")

        # Set secure cookies
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,  # Always use secure in production
            samesite="lax",
            path="/",
            max_age=7 * 24 * 3600  # 7 days
        )
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
            max_age=3600  # 1 hour
        )
        
        # Set security headers
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        })

        return LoginResponse(
            user=UserResponse.from_orm(user).model_dump(),
            access_token=access_token,
            refresh_token=refresh_token
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
            # Check if refresh token is revoked
            if await self.check_token_revocation(refresh_token):
                raise AuthenticationError("Refresh token has been revoked")

            # Verify refresh token
            payload = await self.verify_token(refresh_token)
            
            if payload.get("type") != "refresh":
                raise AuthenticationError(
                    get_error_message("invalid_refresh_token", language)
                )
            
            # Verify token expiration
            exp = payload.get("exp")
            if not exp or datetime.utcnow() > datetime.fromtimestamp(exp):
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
            
            # Set new access token cookie
            cookie_settings = self.get_cookie_settings(request)
            response.set_cookie(
                key="access_token",
                value=f"Bearer {new_access_token}",
                max_age=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                **cookie_settings
            )
            
            # Log successful token refresh
            logger.info("Access token refreshed successfully",
                       extra={"user_id": payload.get("sub")})
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
            
        except (JWTError, AuthenticationError) as e:
            logger.warning(f"Token refresh failed: {str(e)}",
                         extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": get_error_message("token_refresh_failed", language),
                    "error_code": "TOKEN_REFRESH_FAILED"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {str(e)}",
                        extra={"error_type": type(e).__name__})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": get_error_message("token_refresh_failed", language),
                    "error_code": "INTERNAL_SERVER_ERROR"
                }
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
        token: str | None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """Validate token and return payload"""
        if not token:
            raise AuthenticationError("No token provided")
            
        try:
            # Verify the token
            payload = await self.verify_token(token)
            
            # Verify token type is access token
            if payload.get("type") != "access":
                raise AuthenticationError("Invalid token type")
                
            return payload
            
        except (JWTError, AuthenticationError) as e:
            logger.warning(f"Token validation failed: {str(e)}")
            raise AuthenticationError(str(e))
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {str(e)}")
            raise AuthenticationError("Token validation failed")
        
    async def _create_session(self, user_id: str, token_data: Dict[str, Any]) -> str:
        """Create a new session with proper error handling"""
        try:
            async with self.session_lock:  
                session_id = str(uuid.uuid4())
                current_time = datetime.now(timezone.utc)
                
                self.active_sessions[session_id] = {  
                    "user_id": user_id,
                    "created_at": current_time,
                    "last_activity": current_time,
                    "token_data": token_data,
                    "device_info": token_data.get("device_info", {}),
                    "ip_address": token_data.get("ip_address")
                }
                
                logger.debug(
                    "Session created",
                    extra={
                        "session_id": session_id,
                        "user_id": user_id
                    }
                )
                
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
            raise AuthenticationError(
                message="Failed to create session",
                error_code="SESSION_CREATION_ERROR"
            )

    async def _validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate session and update last activity"""
        async with self.session_lock:  # Changed from self._session_lock
            session = self.active_sessions.get(session_id)  # Changed from self._active_sessions
            if not session:
                return None
                
            # Check session expiry
            session_age = datetime.now(timezone.utc) - session["created_at"]
            if session_age > timedelta(minutes=self.settings.SESSION_EXPIRE_MINUTES):
                await self._end_session(session_id)
                return None
            
            # Update last activity
            session["last_activity"] = datetime.now(timezone.utc)
            return session

    async def _end_session(self, session_id: str) -> None:
        """End a session and cleanup"""
        async with self.session_lock:  # Changed from self._session_lock
            if session_id in self.active_sessions:  # Changed from self._active_sessions
                session = self.active_sessions[session_id]
                logger.info(
                    "Session ended",
                    extra={
                        "session_id": session_id,
                        "user_id": session["user_id"],
                        "duration": (datetime.now(timezone.utc) - session["created_at"]).total_seconds()
                    }
                )
                del self.active_sessions[session_id]
    
            
               
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
    
    
        
  
