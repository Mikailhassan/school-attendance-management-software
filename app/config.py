import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, validator
from typing import Optional, List
from datetime import timedelta

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "School Attendance Management System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database Settings
    DATABASE_URL: str
    
    # Security Settings
    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # File Upload Settings
    UPLOAD_FOLDER: str = "uploads"
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS: set = {'png', 'jpg', 'jpeg'}
    
    # Email Settings (if needed)
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Fingerprint Scanner Settings
    SCANNER_TIMEOUT: int = 10  # seconds
    SCANNER_QUALITY_THRESHOLD: int = 60  # minimum quality score
    
    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return v.replace("'", '"')
        return v

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Create settings instance
settings = Settings()

# Additional helper functions
def get_token_expires_delta(minutes: Optional[int] = None) -> timedelta:
    if minutes is None:
        minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    return timedelta(minutes=minutes)

def get_database_url() -> str:
    """Get database URL with fallback options"""
    return settings.DATABASE_URL

def get_fingerprint_settings() -> dict:
    """Get fingerprint scanner settings"""
    return {
        "timeout": settings.SCANNER_TIMEOUT,
        "quality_threshold": settings.SCANNER_QUALITY_THRESHOLD
    }