import asyncio
import logging
from dotenv import load_dotenv
from email_service import EmailService  # Assuming the previous code is saved as email_service.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_email_service():
    """Test the email service with a simple test email"""
    try:
        logger.info("Initializing email service test...")
        email_service = EmailService()
        
        # Test email content
        recipient = "omarmahat702@gmail.com"
        subject = "Yoventa Email Service Test"
        body = """
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Email Service Test</h2>
                    <p>Hello!</p>
                    <p>This is a test email from the Yoventa Attendance Management System.</p>
                    <div style="background-color: #f7fafc; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>If you received this email, it means:</strong></p>
                        <ul>
                            <li>The email service is configured correctly</li>
                            <li>SMTP connection is working</li>
                            <li>Authentication is successful</li>
                        </ul>
                    </div>
                    <p>You can now proceed with using the full email service functionality.</p>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa System Test</strong></p>
                </div>
            </body>
        </html>
        """
        
        # Send test email
        logger.info(f"Sending test email to {recipient}...")
        result = await email_service.send_email_with_retry(
            recipients=[recipient],
            subject=subject,
            body=body
        )
        
        if result:
            logger.info("Test email sent successfully!")
        else:
            logger.error("Failed to send test email")
            
        return result
    
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_email_service())