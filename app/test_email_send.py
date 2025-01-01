import os
from fastapi import FastAPI, HTTPException
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
from pydantic_settings import BaseSettings
from pydantic import EmailStr, SecretStr, Field
from typing import List
from pydantic import BaseModel

# Load settings from .env
class Settings(BaseSettings):
    SMTP_SERVER: str = Field(..., env="SMTP_SERVER")
    SMTP_PORT: int = Field(..., env="SMTP_PORT")
    EMAIL_USERNAME: EmailStr = Field(..., env="EMAIL_USERNAME")
    EMAIL_PASSWORD: SecretStr = Field(..., env="EMAIL_PASSWORD")
    EMAIL_FROM: EmailStr = Field(..., env="EMAIL_FROM")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

class EmailRequest(BaseModel):
    recipients: List[EmailStr]
    subject: str
    body: str

# Email Configuration
conf = ConnectionConfig(
    MAIL_USERNAME="mikailismail260@gmail.com",
    MAIL_PASSWORD="cbfhfrhfr89ff",
    MAIL_FROM="mikailismail260@gmail.com",
    MAIL_PORT=587,  # Port for TLS (secure connection)
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,  # Set this to False because you're using STARTTLS
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# Create FastAPI instance
app = FastAPI()

# Email sending function
async def send_email(subject: str, recipients: List[EmailStr], body: str):
    message = MessageSchema(
        subject=subject,
        recipients=recipients,  # List of email recipients
        body=body,
        subtype="html"  # For HTML emails
    )
    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        return {"status": "success", "message": "Email sent successfully"}
    except ConnectionErrors as e:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

# Route for testing email functionality
@app.post("/test-email/")
async def test_email(email_request: EmailRequest):
    return await send_email(email_request.subject, email_request.recipients, email_request.body)
