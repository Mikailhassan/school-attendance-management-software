import os
from typing import List, Optional
from pydantic import EmailStr, BaseModel
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from datetime import datetime, time
import asyncio
import logging

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
        """
        Initialize email service with secure configuration.
        
        Args:
            config (Optional[EmailConfig]): Email configuration. 
                      If not provided, attempts to load from environment variables.
        """
        # Attempt to load from environment variables if no config is provided
        if config is None:
            try:
                config = EmailConfig(
                    MAIL_USERNAME=os.getenv('EMAIL_USERNAME', ''),
                    MAIL_PASSWORD=os.getenv('EMAIL_PASSWORD', ''),
                    MAIL_FROM=os.getenv('EMAIL_FROM', ''),
                    MAIL_PORT=int(os.getenv('EMAIL_PORT', 587)),
                    MAIL_SERVER=os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
                )
            except ValueError as e:
                logger.error(f"Invalid email configuration: {e}")
                raise

        # Validate configuration
        if not all([config.MAIL_USERNAME, config.MAIL_PASSWORD, config.MAIL_FROM]):
            raise ValueError("Email configuration is incomplete")

        # Create FastMail configuration
        self.conf = ConnectionConfig(**config.dict())
        
        # Initialize FastMail client
        try:
            self.fastmail = FastMail(self.conf)
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
        """
        Send an email with robust error handling and logging.
        
        Args:
            recipients (List[str]): List of recipient email addresses
            subject (str): Email subject
            body (str): Email body content
            subtype (str, optional): Email content subtype. Defaults to "html".
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        # Validate inputs
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

    # Other methods remain the same...

def get_email_service() -> EmailService:
    """
    Factory method to create EmailService with secure configuration.
    
    Returns:
        EmailService: Configured email service instance
    """
    return EmailService()

# Comprehensive test function with improved error handling
async def test_email_service():
    try:
        email_service = get_email_service()
        current_time = datetime.now()
        
        # Test cases
        test_cases = [
            email_service.send_teacher_late_arrival(
                "test@example.com",
                "Mr. Test Teacher",
                current_time.time()
            )
        ]
        
        # Run tests with timeout
        results = await asyncio.wait_for(
            asyncio.gather(*test_cases, return_exceptions=True), 
            timeout=30.0  # 30-second timeout
        )
        
        # Analyze results
        success_count = sum(1 for result in results if result is True)
        print(f"\nEmail Test Results: {success_count}/{len(test_cases)} tests passed")
        
        return all(result is True for result in results)
    
    except asyncio.TimeoutError:
        logger.error("Email tests timed out")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in email service tests: {e}")
        return False

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_email_service())