import os
from typing import List, Optional
from pydantic import EmailStr, BaseModel
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from datetime import datetime, time
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailConfig(BaseModel):
    """Secure configuration model for email settings"""
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

class EmailService:
    def __init__(self, config: Optional[EmailConfig] = None):
        """Initialize email service with secure configuration."""
        # Attempt to load from environment variables if no config is provided
        if config is None:
            try:
                config = EmailConfig(
                    MAIL_USERNAME=os.getenv('EMAIL_USERNAME'),
                    MAIL_PASSWORD=os.getenv('EMAIL_PASSWORD'),
                    MAIL_FROM=os.getenv('EMAIL_FROM'),
                    MAIL_PORT=int(os.getenv('SMTP_PORT', '587')),
                    MAIL_SERVER=os.getenv('SMTP_SERVER', 'smtp.gmail.com')
                )
                logger.info(f"Loaded email configuration for user: {config.MAIL_USERNAME}")
            except ValueError as e:
                logger.error(f"Invalid email configuration: {e}")
                raise

        # Validate configuration
        if not all([config.MAIL_USERNAME, config.MAIL_PASSWORD, config.MAIL_FROM]):
            logger.error("Missing required email configuration values")
            missing = []
            if not config.MAIL_USERNAME: missing.append("EMAIL_USERNAME")
            if not config.MAIL_PASSWORD: missing.append("EMAIL_PASSWORD")
            if not config.MAIL_FROM: missing.append("EMAIL_FROM")
            raise ValueError(f"Email configuration is incomplete. Missing: {', '.join(missing)}")

        # Create FastMail configuration
        self.conf = ConnectionConfig(
            MAIL_USERNAME=config.MAIL_USERNAME,
            MAIL_PASSWORD=config.MAIL_PASSWORD,
            MAIL_FROM=config.MAIL_FROM,
            MAIL_PORT=config.MAIL_PORT,
            MAIL_SERVER=config.MAIL_SERVER,
            MAIL_STARTTLS=config.MAIL_STARTTLS,
            MAIL_SSL_TLS=config.MAIL_SSL_TLS,
            USE_CREDENTIALS=config.USE_CREDENTIALS,
            VALIDATE_CERTS=config.VALIDATE_CERTS
        )
        
        # Initialize FastMail client
        try:
            self.fastmail = FastMail(self.conf)
            logger.info("FastMail client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FastMail: {e}")
            raise

    async def send_email(
        self, 
        recipients: List[str], 
        subject: str, 
        body: str, 
        subtype: str = "html"
    ) -> bool:
        """Send an email with robust error handling and logging."""
        if not recipients or not subject or not body:
            logger.warning("Invalid email parameters")
            return False

        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=subtype
        )

        try:
            await self.fastmail.send_message(message)
            logger.info(f"Email sent successfully to {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {', '.join(recipients)}: {str(e)}")
            return False

    async def send_teacher_late_arrival(self, teacher_email: str, teacher_name: str, arrival_time: time):
        """Send notification when a teacher arrives late"""
        subject = "Late Arrival Notification"
        body = f"""
        <html>
            <body>
                <h2>Late Arrival Recording</h2>
                <p>Dear {teacher_name},</p>
                <p>This email is to confirm that your late arrival has been recorded in the system.</p>
                <p>Arrival Time: {arrival_time.strftime('%I:%M %p')}</p>
                <p>Please ensure to maintain punctuality as per school policies.</p>
                <br>
                <p>Best regards,</p>
                <p>School Administration</p>
            </body>
        </html>
        """
        return await self.send_email([teacher_email], subject, body)

    async def send_school_admin_credentials(self, email: str, name: str, password: str, school_name: str):
        """Send login credentials to newly registered school admin"""
        subject = "School Management System - Admin Account Created"
        body = f"""
        <html>
            <body>
                <h2>Welcome to the School Management System</h2>
                <p>Dear {name},</p>
                <p>Your admin account for {school_name} has been created.</p>
                <p>Your login credentials are:</p>
                <ul>
                    <li>Email: {email}</li>
                    <li>Password: {password}</li>
                </ul>
                <p>For security reasons, please change your password after your first login.</p>
                <p><strong>Important:</strong> As a school admin, you can:</p>
                <ul>
                    <li>Register teachers and students</li>
                    <li>Manage attendance records</li>
                    <li>Generate reports</li>
                    <li>Monitor school activities</li>
                </ul>
                <br>
                <p>Best regards,</p>
                <p>School Management System Team</p>
            </body>
        </html>
        """
        return await self.send_email([email], subject, body)

    async def send_teacher_credentials(self, email: str, name: str, password: str, school_name: str):
        """Send login credentials to newly registered teacher"""
        subject = "School Management System - Teacher Account Created"
        body = f"""
        <html>
            <body>
                <h2>Welcome to {school_name}</h2>
                <p>Dear {name},</p>
                <p>Your teacher account has been created in the School Management System.</p>
                <p>Your login credentials are:</p>
                <ul>
                    <li>Email: {email}</li>
                    <li>Password: {password}</li>
                </ul>
                <p>For security reasons, please change your password after your first login.</p>
                <p>You can use these credentials to:</p>
                <ul>
                    <li>Record your daily attendance</li>
                    <li>View your attendance history</li>
                    <li>Access school announcements</li>
                </ul>
                <br>
                <p>Best regards,</p>
                <p>School Administration</p>
            </body>
        </html>
        """
        return await self.send_email([email], subject, body)

    async def send_parent_portal_access(
        self,
        email: str,
        name: str,
        password: str,
        student_name: str,
        access_link: str,
        school_name: str
    ):
        """Send parent portal access link and credentials to newly registered parent"""
        subject = f"Access Your Child's Attendance Portal - {school_name}"
        body = f"""
        <html>
            <body>
                <h2>Parent Portal Access</h2>
                <p>Dear {name},</p>
                <p>Welcome to the {school_name} Parent Portal. Your account has been created to monitor {student_name}'s attendance.</p>
                <p>Your login credentials are:</p>
                <ul>
                    <li>Email: {email}</li>
                    <li>Password: {password}</li>
                </ul>
                <p>To access the parent portal, please click the link below:</p>
                <p><a href="{access_link}">Access Parent Portal</a></p>
                <p>Through the portal, you can:</p>
                <ul>
                    <li>View your child's daily attendance</li>
                    <li>Monitor attendance history</li>
                    <li>Receive real-time notifications</li>
                    <li>Communicate with teachers</li>
                </ul>
                <p>For security reasons, please change your password after your first login.</p>
                <br>
                <p>Best regards,</p>
                <p>School Administration</p>
            </body>
        </html>
        """
        return await self.send_email([email], subject, body)

async def test_email_service():
    """Test the email service with registration emails"""
    try:
        logger.info("Starting email service test")
        email_service = EmailService()
        test_email = os.getenv('EMAIL_FROM')
        
        if not test_email:
            raise ValueError("No test email address configured")
        
        # Test cases for registration emails
        test_cases = [
            email_service.send_school_admin_credentials(
                test_email,
                "Test Admin",
                "testpass123",
                "Test School"
            ),
            email_service.send_teacher_credentials(
                test_email,
                "Test Teacher",
                "testpass123",
                "Test School"
            ),
            email_service.send_parent_portal_access(
                test_email,
                "Test Parent",
                "testpass123",
                "Test Student",
                "http://example.com/parent-portal",
                "Test School"
            )
        ]
        
        results = await asyncio.wait_for(
            asyncio.gather(*test_cases, return_exceptions=True),
            timeout=30.0
        )
        
        success_count = sum(1 for result in results if result is True)
        logger.info(f"Email Test Results: {success_count}/{len(test_cases)} tests passed")
        
        return all(result is True for result in results)
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_email_service())