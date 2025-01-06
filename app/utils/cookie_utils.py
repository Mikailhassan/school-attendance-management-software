from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Optional, List
from fastapi import Request, Response
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class CookieConfig:
    """Cookie configuration constants"""
    ALLOWED_DOMAINS = ["localhost", "127.0.0.1"]
    ACCESS_TOKEN_KEY = "access_token"
    REFRESH_TOKEN_KEY = "refresh_token"
    TOKEN_PREFIX = "Bearer"
    DEFAULT_REFRESH_PATH = "/api/v1/auth/refresh-token"
    ROOT_PATH = "/"

def get_cookie_settings(request: Request, is_refresh_token: bool = False) -> Dict[str, Any]:
    try:
        host = request.headers.get("host", "").split(":")[0]
        origin = request.headers.get("origin", "")
        is_localhost = host in CookieConfig.ALLOWED_DOMAINS
        
        settings = {
            "httponly": True,
            "secure": not is_localhost,  # False for localhost
            "samesite": "lax",  # Use 'lax' for both localhost and production
            "domain": None,  # Let the browser handle the domain
            "path": CookieConfig.DEFAULT_REFRESH_PATH if is_refresh_token else CookieConfig.ROOT_PATH
        }
        
        logger.debug(f"Cookie settings generated for {host}: {settings}")
        return settings
    except Exception as e:
        logger.error(f"Error getting cookie settings: {str(e)}")
        return {
            "httponly": True,
            "secure": False,  # False for development
            "samesite": "lax",
            "path": CookieConfig.DEFAULT_REFRESH_PATH if is_refresh_token else CookieConfig.ROOT_PATH
        }

def set_auth_cookies(
    response: Response,
    request: Request,
    access_token: str,
    refresh_token: str,
    access_token_expire_minutes: int,
    refresh_token_expire_days: int
) -> None:
    """
    Set authentication cookies with appropriate settings.
    
    Args:
        response: FastAPI response object
        request: FastAPI request object
        access_token: JWT access token
        refresh_token: JWT refresh token
        access_token_expire_minutes: Access token expiration in minutes
        refresh_token_expire_days: Refresh token expiration in days
    """
    try:
        # Get settings for both cookie types
        access_settings = get_cookie_settings(request, is_refresh_token=False)
        refresh_settings = get_cookie_settings(request, is_refresh_token=True)
        
        # Calculate UTC expiration times
        current_time = datetime.now(timezone.utc)
        access_expiration = current_time + timedelta(minutes=access_token_expire_minutes)
        refresh_expiration = current_time + timedelta(days=refresh_token_expire_days)
        
        # Set access token cookie
        response.set_cookie(
            key=CookieConfig.ACCESS_TOKEN_KEY,
            value=f"{CookieConfig.TOKEN_PREFIX} {access_token}",
            expires=access_expiration,
            max_age=access_token_expire_minutes * 60,
            **access_settings
        )
        
        # Set refresh token cookie with explicit domain and path
        refresh_settings["path"] = CookieConfig.DEFAULT_REFRESH_PATH  # Ensure correct refresh path
        response.set_cookie(
            key=CookieConfig.REFRESH_TOKEN_KEY,
            value=f"{CookieConfig.TOKEN_PREFIX} {refresh_token}",
            expires=refresh_expiration,
            max_age=refresh_token_expire_days * 24 * 60 * 60,
            **refresh_settings
        )
        
        logger.debug(
            "Auth cookies set successfully",
            extra={
                "access_expiration": access_expiration.isoformat(),
                "refresh_expiration": refresh_expiration.isoformat(),
                "access_path": access_settings["path"],
                "refresh_path": refresh_settings["path"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error setting auth cookies: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error setting authentication cookies"
        )

def clear_auth_cookies(response: Response, request: Request) -> None:
    """
    Clear authentication cookies.
    
    Args:
        response: FastAPI response object
        request: FastAPI request object
    """
    try:
        # Get settings for both cookie types
        access_settings = get_cookie_settings(request, is_refresh_token=False)
        refresh_settings = get_cookie_settings(request, is_refresh_token=True)
        
        # Ensure correct paths when clearing
        access_settings["path"] = CookieConfig.ROOT_PATH
        refresh_settings["path"] = CookieConfig.DEFAULT_REFRESH_PATH
        
        # Clear access token
        response.delete_cookie(
            key=CookieConfig.ACCESS_TOKEN_KEY,
            **access_settings
        )
        
        # Clear refresh token
        response.delete_cookie(
            key=CookieConfig.REFRESH_TOKEN_KEY,
            **refresh_settings
        )
        
        logger.debug(
            "Auth cookies cleared successfully",
            extra={
                "access_path": access_settings["path"],
                "refresh_path": refresh_settings["path"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error clearing auth cookies: {str(e)}", exc_info=True)
        # Log error but don't raise exception during cleanup

def get_token_from_cookies(request: Request, token_key: str) -> Optional[str]:
    """
    Extract token from cookies.
    
    Args:
        request: FastAPI request object
        token_key: Key of the token to extract
        
    Returns:
        Optional[str]: The token string without Bearer prefix if found, None otherwise
    """
    try:
        cookie_value = request.cookies.get(token_key)
        if not cookie_value:
            logger.debug(f"No cookie found for key: {token_key}")
            return None
            
        if cookie_value.startswith(f"{CookieConfig.TOKEN_PREFIX} "):
            token = cookie_value[len(f"{CookieConfig.TOKEN_PREFIX} "):]
            logger.debug(f"Token extracted successfully from cookie: {token_key}")
            return token
            
        logger.debug(f"Cookie value found but no Bearer prefix: {token_key}")
        return cookie_value
        
    except Exception as e:
        logger.error(f"Error extracting token from cookies: {str(e)}", exc_info=True)
        return None

def validate_cookie_domain(request: Request, allowed_domains: Optional[List[str]] = None) -> bool:
    """
    Validate if the request comes from an allowed domain.
    
    Args:
        request: FastAPI request object
        allowed_domains: Optional list of allowed domains
        
    Returns:
        bool: True if domain is valid, False otherwise
    """
    try:
        domains = allowed_domains or CookieConfig.ALLOWED_DOMAINS
        host = request.headers.get("host", "").split(":")[0]
        
        # Always allow localhost for development
        if host in ["localhost", "127.0.0.1"]:
            return True
            
        is_valid = host in domains
        logger.debug(f"Cookie domain validation: {host} -> {is_valid}")
        return is_valid
        
    except Exception as e:
        logger.error(f"Error validating cookie domain: {str(e)}", exc_info=True)
        return False