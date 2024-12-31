from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Optional
from fastapi import Request

def get_cookie_settings(request: Request) -> Dict[str, Any]:
    """Get appropriate cookie settings based on environment."""
    host = request.headers.get("host", "").split(":")[0]
    is_localhost = host in ["localhost", "127.0.0.1"]
    
    return {
        "httponly": True,
        "secure": not is_localhost,
        "samesite": "lax" if is_localhost else "strict",
        "domain": None if is_localhost else f".{host}",
    }

def get_token_cookie_settings(
    request: Request,
    access_token_expire_minutes: int,
    refresh_token_expire_days: int,
    refresh_path: str = "/api/v1/auth/refresh"
) -> Tuple[Dict[str, Any], Dict[str, Any], datetime, datetime]:
    """Get complete cookie settings for both access and refresh tokens."""
    base_settings = get_cookie_settings(request)
    
    # Access token settings
    access_settings = base_settings.copy()
    access_settings["path"] = "/"
    
    # Refresh token settings
    refresh_settings = base_settings.copy()
    refresh_settings["path"] = refresh_path
    
    # Calculate UTC expiration times
    access_expiration = datetime.now(timezone.utc) + timedelta(minutes=access_token_expire_minutes)
    refresh_expiration = datetime.now(timezone.utc) + timedelta(days=refresh_token_expire_days)
    
    return access_settings, refresh_settings, access_expiration, refresh_expiration

def set_auth_cookies(
    response: Any,
    request: Request,
    access_token: str,
    refresh_token: str,
    access_token_expire_minutes: int,
    refresh_token_expire_days: int
) -> None:
    """Set authentication cookies with appropriate settings."""
    access_settings, refresh_settings, access_exp, refresh_exp = get_token_cookie_settings(
        request,
        access_token_expire_minutes,
        refresh_token_expire_days
    )
    
    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        expires=access_exp,
        max_age=access_token_expire_minutes * 60,
        **access_settings
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        expires=refresh_exp,
        max_age=refresh_token_expire_days * 24 * 60 * 60,
        **refresh_settings
    )

def clear_auth_cookies(
    response: Any,
    request: Request
) -> None:
    """Clear authentication cookies."""
    base_settings = get_cookie_settings(request)
    
    # Clear access token
    access_settings = base_settings.copy()
    access_settings["path"] = "/"
    response.delete_cookie(
        key="access_token",
        **access_settings
    )
    
    # Clear refresh token
    refresh_settings = base_settings.copy()
    refresh_settings["path"] = "/api/v1/auth/refresh"
    response.delete_cookie(
        key="refresh_token",
        **refresh_settings
    )