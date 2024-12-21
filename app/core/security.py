import secrets
import re
from typing import List, Optional
from datetime import datetime, timedelta

from passlib.context import CryptContext
from fastapi import HTTPException
from jose import JWTError, jwt

from app.models import User
from app.core.config import settings
from app.core.logging import logger  
from app.schemas.user.role import  UserRoleEnum, RoleDetails
from app.schemas.user.responses import UserProfileResponse

# Configure password hashing using Passlib with enhanced security parameters
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12,  # Configurable work factor
    bcrypt__min_rounds=10,
    bcrypt__max_rounds=15
)

def get_password_hash(password: str) -> str:
    """
    Hashes a password using bcrypt with configurable complexity.
    
    :param password: The password to hash.
    :return: The hashed password.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies if the given plain password matches the hashed password.
    
    :param plain_password: The plain text password to verify.
    :param hashed_password: The hashed password to check against.
    :return: True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def verify_token(token: str):
    """
    Verifies the JWT token and returns the decoded payload if valid.
    
    :param token: The JWT token to verify.
    :return: The decoded token payload if valid.
    :raises HTTPException: If the token is invalid or expired.
    """
    try:
        # Decode the token using the secret key and the algorithm from your settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"Expired token attempt: {token}")
        raise HTTPException(status_code=401, detail="Token has expired. Please request a new one.")
    except jwt.InvalidTokenError:
        logger.error(f"Invalid token attempt: {token}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

def generate_password_reset_token(email: str) -> str:
    """
    Generates a secure JWT token for password reset with added uniqueness.
    
    :param email: The email address for which the password reset token is generated.
    :return: The generated password reset token.
    """
    reset_token = secrets.token_urlsafe(32)  # Cryptographically secure random token
    expiration = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
    
    payload = {
        "sub": email,
        "exp": expiration,
        "reset_token": reset_token
    }
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.info(f"Password reset token generated for email: {email}")
    return token