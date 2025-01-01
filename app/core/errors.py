from typing import Any, Dict, Optional,Union
from fastapi import HTTPException, status
from app.core.i18n import get_translation
from sqlalchemy.exc import SQLAlchemyError 


class BaseAPIError(Exception):
    """Base exception class for API errors"""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class AuthenticationError(BaseAPIError):
    """Base class for authentication-related errors"""
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            details=details
        )

class InvalidCredentialsException(AuthenticationError):
    """Raised when user credentials are invalid"""
    def __init__(
        self,
        message: str = "Invalid email or password",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="INVALID_CREDENTIALS",
            details=details
        )

class AccountLockedException(AuthenticationError):
    """Raised when account is locked due to too many failed attempts"""
    def __init__(
        self,
        message: str = "Account is temporarily locked",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="ACCOUNT_LOCKED",
            details=details
        )

class RateLimitExceeded(BaseAPIError):
    """Raised when rate limit is exceeded"""
    def __init__(
        self,
        message: str = "Too many requests",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )

class ConfigurationError(BaseAPIError):
    """Raised when there's a configuration-related error"""
    def __init__(
        self,
        message: str = "Configuration error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CONFIG_ERROR",
            details=details
        )

class DatabaseError(BaseAPIError):
    """Raised when there's a database-related error"""
    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DB_ERROR",
            details=details
        )

class TokenError(AuthenticationError):
    """Raised when there's a token-related error"""
    def __init__(
        self,
        message: str = "Invalid or expired token",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="TOKEN_ERROR",
            details=details
        )

class PermissionDenied(BaseAPIError):
    """Raised when user doesn't have required permissions"""
    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED",
            details=details
        )

class ValidationError(BaseAPIError):
    """Raised when input validation fails"""
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )

class NotFoundError(BaseAPIError):
    """Raised when a requested resource is not found"""
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details
        )


def get_error_message(
    error: Union[Exception, HTTPException, str],  # Updated to allow string errors
    language: str = 'en',
    default_message: str = "An unexpected error occurred",
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Formats error messages with proper translation and structure.
    
    Args:
        error: The exception that was raised or error message string
        language: Language code for translation (default: 'en')
        default_message: Fallback message if error type is not recognized
        include_details: Whether to include error details in response
    
    Returns:
        Dict containing formatted error response with message, code, and optional details
    """
    translate = get_translation(language)
    
    # Initialize base response structure
    error_response = {
        "success": False,
        "error_code": "INTERNAL_ERROR",
        "message": default_message,
        "status_code": 500
    }
    
    # Handle string error messages
    if isinstance(error, str):
        error_response.update({
            "message": translate(error),
            "error_code": "GENERAL_ERROR"
        })
        return error_response

    if isinstance(error, HTTPException):
        error_response.update({
            "error_code": "HTTP_ERROR",
            "message": translate(str(error.detail)),
            "status_code": error.status_code
        })
        
    elif isinstance(error, SQLAlchemyError):
        error_response.update({
            "error_code": "DB_ERROR",
            "message": translate("Database error occurred"),
            "status_code": 500
        })
        
    elif hasattr(error, 'error_code') and hasattr(error, 'status_code'):
        error_response.update({
            "error_code": error.error_code,
            "message": translate(str(error.message)),
            "status_code": error.status_code
        })
        
        if include_details and hasattr(error, 'details') and error.details:
            error_response["details"] = error.details
            
    elif isinstance(error, ValueError):
        error_response.update({
            "error_code": "VALIDATION_ERROR",
            "message": translate(str(error)),
            "status_code": 422
        })
    
    # Add debug information in non-production environments
    if include_details:
        error_response["error_type"] = error.__class__.__name__
        
        if not is_production():  
            import traceback
            error_response["traceback"] = traceback.format_exc()
    
    return error_response