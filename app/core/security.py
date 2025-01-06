# app/core/security.py

from datetime import datetime, timedelta
import secrets
import re
import string
from typing import Dict, Optional, Any, Union
from jose import JWTError, jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import logger
from app.schemas.user.role import UserRoleEnum

class SecurityConfig:
    """Security configuration constants"""
    MIN_PASSWORD_LENGTH = 12
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_ROUNDS = 12
    TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    RESET_TOKEN_EXPIRE_HOURS = 1
    PASSWORD_REGEX = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$"
    )

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=SecurityConfig.PASSWORD_ROUNDS
)

async def verify_token(token: str, token_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify JWT token and optionally check token type
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if token_type and payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return payload
        
    except JWTError as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_token(
    data: Dict[str, Any],
    token_type: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT token with specified type and expiration"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=SecurityConfig.TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "type": token_type,
        "jti": secrets.token_urlsafe(32)
    })

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def generate_password_reset_token(email: str) -> str:
    """Generate password reset token"""
    data = {
        "sub": email,
        "reset_id": secrets.token_urlsafe(32)
    }
    return create_token(data, "reset", timedelta(hours=SecurityConfig.RESET_TOKEN_EXPIRE_HOURS))

def create_access_token(user_id: Union[int, str], role: UserRoleEnum) -> str:
    """Create access token with user ID and role"""
    data = {
        "sub": str(user_id),
        "role": role.value
    }
    return create_token(data, "access", timedelta(minutes=SecurityConfig.TOKEN_EXPIRE_MINUTES))

def create_refresh_token(user_id: Union[int, str]) -> str:
    """Create refresh token with user ID"""
    data = {"sub": str(user_id)}
    return create_token(data, "refresh", timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS))

def generate_temporary_password(length: int = SecurityConfig.MIN_PASSWORD_LENGTH) -> str:
    """Generate secure temporary password"""
    if length < SecurityConfig.MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password length must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters")
    if length > SecurityConfig.MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password length must not exceed {SecurityConfig.MAX_PASSWORD_LENGTH} characters")
    
    chars = string.ascii_letters + string.digits + "@$!%*?&"
    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))
        if (any(c.islower() for c in password) 
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "@$!%*?&" for c in password)):
            return password

class TokenHandler:
    """JWT token generation and validation"""

    @staticmethod
    def create_token(
        data: Dict[str, Any],
        token_type: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT token with specified type and expiration"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            if token_type == TokenType.ACCESS:
                expire = datetime.utcnow() + timedelta(
                    minutes=SecurityConfig.TOKEN_EXPIRE_MINUTES
                )
            elif token_type == TokenType.REFRESH:
                expire = datetime.utcnow() + timedelta(
                    days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS
                )
            elif token_type == TokenType.RESET:
                expire = datetime.utcnow() + timedelta(
                    hours=SecurityConfig.RESET_TOKEN_EXPIRE_HOURS
                )
            else:
                expire = datetime.utcnow() + timedelta(minutes=15)

        to_encode.update({
            "exp": expire,
            "type": token_type,
            "jti": secrets.token_urlsafe(32)  # Unique token ID
        })

        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

    @staticmethod
    def verify_token(
        token: str,
        token_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify JWT token and optionally check token type
        
        Args:
            token: JWT token to verify
            token_type: Expected token type (optional)
            
        Returns:
            Dict containing token payload
            
        Raises:
            HTTPException: If token is invalid or wrong type
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Verify token type if specified
            if token_type and payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
            return payload
            
        except JWTError as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def generate_password_reset_token(email: str) -> str:
    """Generate password reset token"""
    data = {
        "sub": email,
        "reset_id": secrets.token_urlsafe(32)
    }
    return TokenHandler.create_token(data, TokenType.RESET)

def create_access_token(user_id: Union[int, str], role: UserRoleEnum) -> str:
    """Create access token with user ID and role"""
    data = {
        "sub": str(user_id),
        "role": role.value
    }
    return TokenHandler.create_token(data, TokenType.ACCESS)

def create_refresh_token(user_id: Union[int, str]) -> str:
    """Create refresh token with user ID"""
    data = {"sub": str(user_id)}
    return TokenHandler.create_token(data, TokenType.REFRESH)
def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent directory traversal attacks"""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

def is_secure_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Check if a password meets security requirements.
    Returns (is_secure, error_message)
    """
    if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters long"
    
    if len(password) > SecurityConfig.MAX_PASSWORD_LENGTH:
        return False, f"Password must not exceed {SecurityConfig.MAX_PASSWORD_LENGTH} characters"
        
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
        
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
        
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
        
    if not any(c in "@$!%*?&" for c in password):
        return False, "Password must contain at least one special character (@$!%*?&)"
        
    return True, None

def compare_passwords_securely(password1: str, password2: str) -> bool:
    """
    Compare two passwords in a timing-safe manner to prevent timing attacks
    """
    return secrets.compare_digest(password1.encode(), password2.encode())