import asyncio
import logging
import socket
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Email Configuration
conf = ConnectionConfig(
    MAIL_USERNAME="api",  # Mailtrap username
    MAIL_PASSWORD="dc46307ac3da97bf55533333db23c4a5",  # Mailtrap password
    MAIL_FROM="smtp@mailtrap.io",  # Sender email
    MAIL_PORT=587,  # Mailtrap port
    MAIL_SERVER="live.smtp.mailtrap.io",  # Mailtrap server
    MAIL_STARTTLS=True,  # Enable STARTTLS
    MAIL_SSL_TLS=False,  # SSL/TLS not used
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def test_network():
    """Test network connectivity to SMTP server"""
    try:
        # Test DNS resolution
        logger.info("Testing DNS resolution...")
        smtp_ip = socket.gethostbyname('live.smtp.mailtrap.io')
        logger.info(f"SMTP server IP: {smtp_ip}")
        
        # Test socket connection
        logger.info("Testing socket connection...")
        sock = socket.create_connection(('live.smtp.mailtrap.io', 587), timeout=10)
        sock.close()
        logger.info("Socket connection successful")
        return True
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed: {e}")
        return False
    except socket.timeout as e:
        logger.error(f"Connection timed out: {e}")
        return False
    except Exception as e:
        logger.error(f"Network test failed: {e}")
        return False

async def test_email():
    """Test email sending functionality"""
    # First test network connectivity
    if not await test_network():
        logger.error("Network connectivity test failed. Skipping email test.")
        return
    
    logger.info("Starting email test...")
    
    try:
        # Create FastMail instance
        logger.info("Initializing FastMail...")
        mail = FastMail(conf)
        
        # Create test message
        logger.info("Creating test message...")
        message = MessageSchema(
            subject="Test Email from FastAPI with Mailtrap",
            recipients=["mikailismail260@gmail.com"],  # Replace with the recipient email
            body="""
            <html>
                <body>
                    <h1>Test Email</h1>
                    <p>This is a test email sent from FastAPI mail using Mailtrap</p>
                    <p>If you receive this, the email service is working correctly!</p>
                </body>
            </html>
            """,
            subtype="html"
        )

        # Attempt to send email
        logger.info("Attempting to send email...")
        await mail.send_message(message)
        logger.info("Email sent successfully!")
        
    except ConnectionError as e:
        logger.error(f"Connection error occurred: {e}")
        logger.error("Please check your network connection and firewall settings.")
    except TimeoutError as e:
        logger.error(f"Connection timed out: {e}")
        logger.error("The SMTP server took too long to respond.")
    except Exception as e:
        logger.error(f"Failed to send email. Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        # Print exception traceback for detailed debugging
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("Starting SMTP test script...")
    try:
        asyncio.run(test_email())
    except KeyboardInterrupt:
        logger.info("Test cancelled by user.")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
    finally:
        logger.info("Test script completed.")
