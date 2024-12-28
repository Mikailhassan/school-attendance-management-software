# app/core/security.py
import secrets
import re
from typing import List, Optional
from datetime import datetime, timedelta
import string

from passlib.context import CryptContext
from fastapi import HTTPException
from jose import JWTError, jwt

from app.models import User
from app.core.config import settings
from app.core.logging import logger  
from app.schemas.user.role import UserRoleEnum, RoleDetails
from app.schemas.user.responses import UserProfileResponse

# Configure password hashing using Passlib with enhanced security parameters
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12,  # Configurable work factor
    bcrypt__min_rounds=10,
    bcrypt__max_rounds=15
)

def generate_temporary_password(length: int = 12) -> str:
    """
    Generates a secure temporary password with specified complexity requirements.
    
    The generated password will include:
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    - Minimum length of 12 characters (configurable)
    
    :param length: The desired length of the password (default: 12)
    :return: A secure temporary password string
    :raises ValueError: If the requested length is too short to meet complexity requirements
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    # Exclude ambiguous special characters to avoid confusion
    special = "!@#$%^&*()_+-=[]{}|"

    # Ensure at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]

    # Fill the rest with random characters from all sets
    all_characters = lowercase + uppercase + digits + special
    
    # Generate remaining characters
    for _ in range(length - 4):
        password.append(secrets.choice(all_characters))

    # Shuffle the password characters
    secrets.SystemRandom().shuffle(password)
    
    # Join characters into final password
    final_password = ''.join(password)
    
    # Verify password meets requirements
    if not all([
        re.search(r'[a-z]', final_password),
        re.search(r'[A-Z]', final_password),
        re.search(r'\d', final_password),
        re.search(f'[{re.escape(special)}]', final_password)
    ]):
        # Recursively generate new password if requirements not met
        return generate_temporary_password(length)
        
    return final_password

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
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        print(f"Decoded payload: {payload}")  # For debugging
        return payload
    except Exception as e:
        print(f"Token verification error: {str(e)}")  # For debugging
        raise HTTPException(status_code=401, detail="Could not validate credentials")


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