import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, validator, EmailStr
from typing import Optional, List, Dict
from datetime import timedelta

class Settings(BaseSettings):
    APP_NAME: str = "School Attendance Management System"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    SECRET_KEY: SecretStr = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")
    
    UPLOAD_FOLDER: str = Field(default="uploads", env="UPLOAD_FOLDER")
    MAX_CONTENT_LENGTH: int = Field(default=16 * 1024 * 1024, env="MAX_CONTENT_LENGTH")
    ALLOWED_EXTENSIONS: set = {'png', 'jpg', 'jpeg', 'gif'}
    
    SMTP_SERVER: Optional[str] = Field(default=None, env="SMTP_SERVER")
    SMTP_PORT: Optional[int] = Field(default=None, env="SMTP_PORT")
    SMTP_USERNAME: Optional[EmailStr] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[SecretStr] = Field(default=None, env="SMTP_PASSWORD")
    
    SCANNER_TIMEOUT: int = Field(default=10, env="SCANNER_TIMEOUT")
    SCANNER_QUALITY_THRESHOLD: int = Field(default=60, env="SCANNER_QUALITY_THRESHOLD")

    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")

    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator('ALLOWED_EXTENSIONS', pre=True)
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            return set(ext.strip().lower() for ext in v.split(","))
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

    def get_email_config(self) -> Dict[str, Optional[str]]:
        return {
            "SMTP_SERVER": self.SMTP_SERVER,
            "SMTP_PORT": self.SMTP_PORT,
            "SMTP_USERNAME": self.SMTP_USERNAME.email if self.SMTP_USERNAME else None,
            "SMTP_PASSWORD": self.SMTP_PASSWORD.get_secret_value() if self.SMTP_PASSWORD else None
        }

settings = Settings()

def get_token_expires_delta(minutes: Optional[int] = None) -> timedelta:
    if minutes is None:
        minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    return timedelta(minutes=minutes)

def get_database_url() -> str:
    return settings.DATABASE_URL

def get_fingerprint_settings() -> dict:
    return {
        "timeout": settings.SCANNER_TIMEOUT,
        "quality_threshold": settings.SCANNER_QUALITY_THRESHOLD
    }

def get_upload_folder() -> str:
    folder = os.path.abspath(settings.UPLOAD_FOLDER)
    os.makedirs(folder, exist_ok=True)
    return folder