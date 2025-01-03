import asyncio
import logging
import socket
import ssl
import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Email Configuration
conf = ConnectionConfig(
    MAIL_USERNAME="mikailismail260@gmail.com",
    MAIL_PASSWORD="vbdp dtvn tjyn oiao",  # App password for Gmail
    MAIL_FROM="mikailismail260@gmail.com",
    MAIL_PORT=465,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TIMEOUT=10,  # Increased timeout for slower connections
)

async def test_network():
    """Test network connectivity to SMTP server."""
    try:
        # Test DNS resolution
        logger.info("Testing DNS resolution...")
        smtp_ip = socket.gethostbyname('smtp.gmail.com')
        logger.info(f"SMTP server IP: {smtp_ip}")

        # Test basic ping
        logger.info("Testing ping to 8.8.8.8...")
        ping_result = os.system("ping -c 1 8.8.8.8")
        logger.info(f"Ping result: {'Success' if ping_result == 0 else 'Failed'}")

        # Test HTTPS connection (port 443)
        logger.info("Testing HTTPS connection...")
        https_context = ssl.create_default_context()
        with socket.create_connection(("google.com", 443), timeout=10) as sock:
            with https_context.wrap_socket(sock, server_hostname="google.com") as ssock:
                logger.info("HTTPS connection successful")

        # Test SMTP connection
        logger.info("Testing SMTP connection...")
        smtp_context = ssl.create_default_context()
        with socket.create_connection((smtp_ip, 465), timeout=10) as sock:
            with smtp_context.wrap_socket(sock, server_hostname='smtp.gmail.com') as ssock:
                logger.info("SSL/TLS connection successful")

        return True
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed: {e}")
    except socket.timeout as e:
        logger.error(f"Connection timed out: {e}")
    except Exception as e:
        logger.error(f"Network test failed: {type(e).__name__}: {str(e)}")
    return False

async def test_email():
    """Test email sending functionality."""
    logger.info("Starting email test...")

    try:
        # Create FastMail instance
        logger.info("Initializing FastMail...")
        mail = FastMail(conf)

        # Create test message
        logger.info("Creating test message...")
        message = MessageSchema(
            subject="Test Email from FastAPI with Gmail",
            recipients=["omarmahat702@gmail.com"],
            body="""
            <html>
                <body>
                    <h1>Test Email</h1>
                    <p>This is a test email sent from FastAPI mail using Gmail SMTP.</p>
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

    except Exception as e:
        logger.error(f"Failed to send email. Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("Starting SMTP test script...")
    try:
        # First test network connectivity
        asyncio.run(test_network())
        # If network test passes, try email
        asyncio.run(test_email())
    except KeyboardInterrupt:
        logger.info("Test cancelled by user.")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
    finally:
        logger.info("Test script completed.")
