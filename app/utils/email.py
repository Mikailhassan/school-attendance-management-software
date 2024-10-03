from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr, BaseModel
from typing import List
from functools import lru_cache

class EmailConfig(BaseModel):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_TLS: bool
    MAIL_SSL: bool

    class Config:
        env_file = ".env"

@lru_cache()
def get_email_config() -> EmailConfig:
    return EmailConfig()

def get_connection_config(email_config: EmailConfig = get_email_config()) -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=email_config.MAIL_USERNAME,
        MAIL_PASSWORD=email_config.MAIL_PASSWORD,
        MAIL_FROM=email_config.MAIL_FROM,
        MAIL_PORT=email_config.MAIL_PORT,
        MAIL_SERVER=email_config.MAIL_SERVER,
        MAIL_TLS=email_config.MAIL_TLS,
        MAIL_SSL=email_config.MAIL_SSL,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )

async def send_email(
    recipients: List[EmailStr],
    subject: str,
    body: str,
    connection_config: ConnectionConfig = get_connection_config()
):
    """
    Send an email to the specified recipients.
    """
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype="html"
    )

    fm = FastMail(connection_config)

    try:
        await fm.send_message(message)
        print(f"Email sent to {', '.join(recipients)}: {subject}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

# Example usage
# async def send_welcome_email(user_email: EmailStr):
#     await send_email(
#         recipients=[user_email],
#         subject="Welcome to Our School System",
#         body="<h1>Welcome!</h1><p>Thank you for joining our school system.</p>"
#     )