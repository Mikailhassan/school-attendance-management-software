import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, validator, EmailStr, AnyHttpUrl, constr
from typing import Optional, List, Dict, Set
from datetime import timedelta

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "School Attendance Management System"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database Settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Authentication Settings
    SECRET_KEY: SecretStr = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")
    
    # File Upload Settings
    UPLOAD_FOLDER: str = Field(default="uploads", env="UPLOAD_FOLDER")
    MAX_CONTENT_LENGTH: int = Field(default=16 * 1024 * 1024, env="MAX_CONTENT_LENGTH")
    ALLOWED_EXTENSIONS: Set[str] = Field(default={'png', 'jpg', 'jpeg', 'gif'}, env="ALLOWED_EXTENSIONS")
    
    # Email Settings
    SMTP_SERVER: Optional[str] = Field(default=None, env="SMTP_SERVER")
    SMTP_PORT: Optional[int] = Field(default=None, env="SMTP_PORT")
    SMTP_USERNAME: Optional[EmailStr] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[SecretStr] = Field(default=None, env="SMTP_PASSWORD")
    
    # Fingerprint Scanner Settings
    SCANNER_TIMEOUT: int = Field(default=10, env="SCANNER_TIMEOUT")
    SCANNER_QUALITY_THRESHOLD: int = Field(default=60, env="SCANNER_QUALITY_THRESHOLD")

    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")

    # Admin Settings
    SUPER_ADMIN_EMAIL: EmailStr = Field(..., env="SUPER_ADMIN_EMAIL")
    SUPER_ADMIN_PASSWORD: SecretStr = Field(..., env="SUPER_ADMIN_PASSWORD")

    # SMS Settings
    SMS_PROVIDER: str = Field(default="INFOBIP", env="SMS_PROVIDER")
    SMS_ENABLED: bool = Field(default=True, env="SMS_ENABLED")
    
    # Infobip Settings - Updated to handle URL validation
    INFOBIP_BASE_URL: str = Field(..., env="INFOBIP_BASE_URL")
    INFOBIP_API_KEY: SecretStr = Field(..., env="INFOBIP_API_KEY")
    INFOBIP_SENDER_ID: str = Field(default="School", env="INFOBIP_SENDER_ID")
    
    # SMS Rate Limiting
    SMS_RATE_LIMIT_PER_MINUTE: int = Field(default=10, env="SMS_RATE_LIMIT_PER_MINUTE")
    SMS_RATE_LIMIT_PER_HOUR: int = Field(default=100, env="SMS_RATE_LIMIT_PER_HOUR")
    SMS_RATE_LIMIT_PER_DAY: int = Field(default=1000, env="SMS_RATE_LIMIT_PER_DAY")
    
    # SMS Templates
    SMS_TEMPLATES: Dict[str, str] = Field(
        default={
            "attendance_check_in": "Dear parent, {student_name} has checked in to school at {time}.",
            "attendance_check_out": "Dear parent, {student_name} has checked out of school at {time}.",
            "teacher_reminder": "Dear {teacher_name}, please remember to mark your attendance for today.",
            "emergency_alert": "URGENT: {message}",
        },
        env="SMS_TEMPLATES"
    )

    # Validators
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
    
    @validator('SMS_TEMPLATES', pre=True)
    def parse_sms_templates(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
                return cls.__fields__['SMS_TEMPLATES'].default
        return v

    @validator('INFOBIP_SENDER_ID')
    def validate_sender_id(cls, v):
        if not 3 <= len(v) <= 11:
            raise ValueError("Sender ID must be between 3 and 11 characters")
        return v

    @validator('INFOBIP_BASE_URL')
    def validate_infobip_url(cls, v: str) -> str:
        # If URL doesn't start with http:// or https://, prepend https://
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        
        # Validate the URL format
        try:
            from pydantic import AnyHttpUrl
            AnyHttpUrl(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid URL format: {v}. Please provide a valid URL.")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

# Initialize settings
settings = Settings()

# Helper Functions
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

def get_logging_config() -> Dict[str, Optional[str]]:
    return {
        "log_level": settings.LOG_LEVEL,
        "log_file": settings.LOG_FILE
    }

def get_sms_settings() -> dict:
    return {
        "provider": settings.SMS_PROVIDER,
        "enabled": settings.SMS_ENABLED,
        "base_url": settings.INFOBIP_BASE_URL,
        "api_key": settings.INFOBIP_API_KEY.get_secret_value(),
        "sender_id": settings.INFOBIP_SENDER_ID,
        "rate_limits": {
            "per_minute": settings.SMS_RATE_LIMIT_PER_MINUTE,
            "per_hour": settings.SMS_RATE_LIMIT_PER_HOUR,
            "per_day": settings.SMS_RATE_LIMIT_PER_DAY
        }
    }

def get_sms_template(template_name: str, **kwargs) -> str:
    template = settings.SMS_TEMPLATES.get(template_name)
    if template is None:
        raise ValueError(f"SMS template '{template_name}' not found")
    return template.format(**kwargs)