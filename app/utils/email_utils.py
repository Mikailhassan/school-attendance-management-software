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
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool

    class Config:
        env_file = ".env"

@lru_cache()
def get_email_config() -> EmailConfig:
    return EmailConfig(
        MAIL_USERNAME="techloomsolns@gmail.com",
        MAIL_PASSWORD="TECHLOOM2024@",
        MAIL_FROM="no_reply@gmail.com",
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False
    )

def get_connection_config(email_config: EmailConfig = get_email_config()) -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=email_config.MAIL_USERNAME,
        MAIL_PASSWORD=email_config.MAIL_PASSWORD,
        MAIL_FROM=email_config.MAIL_FROM,
        MAIL_PORT=email_config.MAIL_PORT,
        MAIL_SERVER=email_config.MAIL_SERVER,
        MAIL_STARTTLS=email_config.MAIL_STARTTLS,
        MAIL_SSL_TLS=email_config.MAIL_SSL_TLS,
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

async def send_school_welcome_email(school_email: EmailStr, school_name: str):
    """Send a welcome email to a newly registered school"""
    await send_email(
        recipients=[school_email],
        subject="Welcome to Youventa Attendance Management System",
        body=f"""
        <h1>Welcome, {school_name}!</h1>
        <p>Thank you for joining Youventa Attendance Management System. We're excited to help you manage your school's attendance efficiently.</p>
        <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
        """
    )

async def send_student_check_notification(parent_email: EmailStr, student_name: str, check_type: str):
    """Send a notification to parents when their child checks in or out"""
    action = "checked in to" if check_type == "check_in" else "checked out of"
    await send_email(
        recipients=[parent_email],
        subject=f"Student {check_type.capitalize()} Notification",
        body=f"""
        <h1>Student Attendance Update</h1>
        <p>Dear Parent,</p>
        <p>This is to inform you that {student_name} has successfully {action} school.</p>
        <p>If you have any questions, please contact the school administration.</p>
        """
    )

async def send_teacher_reminder(teacher_email: EmailStr, teacher_name: str, missing_action: str):
    """Send a reminder to teachers if they forget to check in or out"""
    await send_email(
        recipients=[teacher_email],
        subject="Attendance Check Reminder",
        body=f"""
        <h1>Attendance Check Reminder</h1>
        <p>Dear {teacher_name},</p>
        <p>This is a friendly reminder that you have not {missing_action} today. Please remember to mark your attendance regularly.</p>
        <p>If you have any issues with the attendance system, please contact the school administration.</p>
        """
    )

# Example usage
# await send_school_welcome_email("school@example.com", "Sunshine Elementary")
# await send_student_check_notification("parent@example.com", "John Doe", "check_in")
# await send_teacher_reminder("teacher@example.com", "Ms. Smith", "checked in")