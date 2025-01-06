import os
import base64
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

    PRODUCTION: bool = Field(default=False, env="PRODUCTION")

    # Rate Limiting Settings
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=100, env="RATE_LIMIT_MAX_REQUESTS")
    RATE_LIMIT_TIME_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")

    # Security Settings
    FAILED_ATTEMPTS: int = Field(default=5, env="FAILED_LOGIN_ATTEMPTS")
    DURATION_MINUTES: int = Field(default=30, env="SESSION_EXPIRE_MINUTES")
    LOCKOUT_DURATION_MINUTES: int = Field(default=15, env="LOCKOUT_DURATION_MINUTES")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, env="FAILED_LOGIN_ATTEMPTS")
    
    # Cookie Settings
    COOKIE_DOMAIN: str = Field(default="localhost", env="COOKIE_DOMAIN")
    COOKIE_SECURE: bool = Field(default=True, env="COOKIE_SECURE")
    COOKIE_HTTPONLY: bool = Field(default=True, env="COOKIE_HTTPONLY")
    COOKIE_SAMESITE: str = Field(default="lax", env="COOKIE_SAMESITE")
    COOKIE_PATH: str = Field(default="/", env="COOKIE_PATH")

    # Authentication Settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    TOKEN_ISSUER: str = Field(default="school_attendance_system", env="TOKEN_ISSUER")
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ],
        env="ALLOWED_ORIGINS"
    )
    credentials: bool = Field(default=True, env="CREDENTIALS")
 
    # File Upload Settings
    UPLOAD_FOLDER: str = Field(default="uploads", env="UPLOAD_FOLDER")
    MAX_CONTENT_LENGTH: int = Field(default=16 * 1024 * 1024, env="MAX_CONTENT_LENGTH")
    ALLOWED_EXTENSIONS: Set[str] = Field(default={'png', 'jpg', 'jpeg', 'gif'}, env="ALLOWED_EXTENSIONS")
    
    # Email Settings
    SMTP_SERVER: Optional[str] = Field(default=None, env="SMTP_SERVER")
    SMTP_PORT: Optional[int] = Field(default=None, env="SMTP_PORT")
    EMAIL_USERNAME: Optional[str] = Field(default=None, env="EMAIL_USERNAME")
    EMAIL_PASSWORD: Optional[str] = Field(default=None, env="EMAIL_PASSWORD")
    EMAIL_FROM: Optional[str] = Field(default=None, env="EMAIL_FROM")
    MAIL_USE_TLS: bool = Field(default=False, env="MAIL_USE_TLS")
    
    # Fingerprint Scanner Settings
    SCANNER_TIMEOUT: int = Field(default=10, env="SCANNER_TIMEOUT")
    SCANNER_QUALITY_THRESHOLD: int = Field(default=60, env="SCANNER_QUALITY_THRESHOLD")

    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")

    # Admin Settings
    SUPER_ADMIN_EMAIL: EmailStr = Field(..., env="SUPER_ADMIN_EMAIL")
    SUPER_ADMIN_PASSWORD: str = Field(..., env="SUPER_ADMIN_PASSWORD")

    # SMS Settings
    SMS_PROVIDER: str = Field(default="INFOBIP", env="SMS_PROVIDER")
    SMS_ENABLED: bool = Field(default=True, env="SMS_ENABLED")
    
    # Infobip Settings
    INFOBIP_BASE_URL: str = Field(..., env="INFOBIP_BASE_URL")
    INFOBIP_API_KEY: str = Field(..., env="INFOBIP_API_KEY")
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

    @validator('SECRET_KEY')
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is properly formatted and encoded"""
        # Convert to bytes if it's a string
        if isinstance(v, str):
            v = v.encode()
        
        # Ensure minimum length
        if len(v) < 32:
            from hashlib import sha256
            v = sha256(v).digest()
        
        # Return base64 encoded string
        return base64.urlsafe_b64encode(v).decode()

    @validator('ALLOWED_ORIGINS', pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
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
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        try:
            from pydantic import AnyHttpUrl
            AnyHttpUrl(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid URL format: {v}. Please provide a valid URL.")

    def get_jwt_key(self) -> str:
        """Return the properly encoded secret key for JWT operations"""
        if isinstance(self.SECRET_KEY, str):
            return self.SECRET_KEY
        return base64.urlsafe_b64encode(self.SECRET_KEY).decode()

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

def get_jwt_settings() -> dict:
    return {
        "secret_key": settings.get_jwt_key(),
        "algorithm": settings.ALGORITHM,
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_expire_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
        "token_issuer": settings.TOKEN_ISSUER
    }

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

def get_email_settings() -> dict:
    return {
        "smtp_server": settings.SMTP_SERVER,
        "smtp_port": settings.SMTP_PORT,
        "username": settings.EMAIL_USERNAME,
        "password": settings.EMAIL_PASSWORD,
        "from_email": settings.EMAIL_FROM,
        "use_tls": settings.MAIL_USE_TLS
    }

def get_sms_settings() -> dict:
    return {
        "provider": settings.SMS_PROVIDER,
        "enabled": settings.SMS_ENABLED,
        "base_url": settings.INFOBIP_BASE_URL,
        "api_key": settings.INFOBIP_API_KEY,
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