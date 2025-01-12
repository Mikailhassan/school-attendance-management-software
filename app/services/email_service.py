import os
from typing import List, Optional
from pydantic import BaseModel, EmailStr, validator
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from datetime import datetime, time
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailConfig(BaseModel):
    """Email configuration with secure defaults and validation"""
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int = 465
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Yoventa Attendance System"
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = True
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    TIMEOUT: int = 10  # Added timeout configuration

    @validator('MAIL_PORT')
    def validate_port(cls, v):
        if v not in [465, 587]:
            raise ValueError(f"Invalid SMTP port: {v}. Must be 465 (SSL) or 587 (STARTTLS)")
        return v

class EmailService:
    def __init__(self, config: Optional[EmailConfig] = None):
        """Initialize email service with secure configuration."""
        load_dotenv()
        
        if config is None:
            try:
                config = EmailConfig(
                    MAIL_USERNAME=os.getenv('EMAIL_USERNAME'),
                    MAIL_PASSWORD=os.getenv('EMAIL_PASSWORD'),
                    MAIL_FROM=os.getenv('EMAIL_FROM'),
                    MAIL_PORT=int(os.getenv('SMTP_PORT', '465')),
                    MAIL_SERVER=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                    MAIL_FROM_NAME=os.getenv('MAIL_FROM_NAME', 'Yoventa Attendance System'),
                    TIMEOUT=int(os.getenv('SMTP_TIMEOUT', '10'))
                )
                logger.info(f"Loaded email configuration for user: {config.MAIL_USERNAME}")
            except ValueError as e:
                logger.error(f"Invalid email configuration: {e}")
                raise

        # Validate configuration
        if not all([config.MAIL_USERNAME, config.MAIL_PASSWORD, config.MAIL_FROM]):
            missing = []
            if not config.MAIL_USERNAME: missing.append("EMAIL_USERNAME")
            if not config.MAIL_PASSWORD: missing.append("EMAIL_PASSWORD")
            if not config.MAIL_FROM: missing.append("EMAIL_FROM")
            raise ValueError(f"Email configuration is incomplete. Missing: {', '.join(missing)}")

        # Create FastMail configuration with timeout
        self.conf = ConnectionConfig(
            MAIL_USERNAME=config.MAIL_USERNAME,
            MAIL_PASSWORD=config.MAIL_PASSWORD,
            MAIL_FROM=config.MAIL_FROM,
            MAIL_PORT=config.MAIL_PORT,
            MAIL_SERVER=config.MAIL_SERVER,
            MAIL_STARTTLS=config.MAIL_STARTTLS,
            MAIL_SSL_TLS=config.MAIL_SSL_TLS,
            USE_CREDENTIALS=config.USE_CREDENTIALS,
            VALIDATE_CERTS=config.VALIDATE_CERTS,
            MAIL_FROM_NAME=config.MAIL_FROM_NAME,
            TIMEOUT=config.TIMEOUT  # Added timeout to connection config
        )

        try:
            self.fastmail = FastMail(self.conf)
            logger.info("FastMail client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FastMail: {e}")
            raise

    async def send_email_with_retry(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        subtype: str = "html",
        max_retries: int = 3
    ) -> bool:
        """Send an email with retry mechanism and detailed error logging"""
        for attempt in range(max_retries):
            try:
                if not recipients or not subject or not body:
                    logger.warning("Invalid email parameters")
                    return False

                message = MessageSchema(
                    subject=subject,
                    recipients=recipients,
                    body=body,
                    subtype=subtype
                )

                # More detailed logging
                logger.info(f"Attempt {attempt + 1}: Sending email to {', '.join(recipients)}")
                await self.fastmail.send_message(message)
                logger.info(f"Email sent successfully to {', '.join(recipients)}")
                return True

            except Exception as e:
                wait_time = 2 ** attempt
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed:")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error details: {str(e)}")
                import traceback
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to send email after {max_retries} attempts")
                    return False

    async def send_school_admin_credentials(self, email: str, name: str, password: str, school_name: str):
        """Send login credentials to newly registered school admin"""
        subject = "Welcome to Yoventa Attendance Management System - Admin Account Created"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Welcome to Yoventa Attendance Management System</h2>
                    <p>Dear {name},</p>
                    <p>Your admin account for {school_name} has been successfully created in the Yoventa Attendance Management System.</p>
                    <div style="background-color: #f7fafc; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="font-weight: bold;">Your login credentials are:</p>
                        <ul>
                            <li>Email: {email}</li>
                            <li>Password: {password}</li>
                        </ul>
                    </div>
                    <p style="color: #e53e3e;">For security reasons, please change your password after your first login.</p>
                    <div style="margin: 20px 0;">
                        <p><strong>As a school administrator, you have access to:</strong></p>
                        <ul>
                            <li>Dashboard with real-time attendance analytics</li>
                            <li>Staff and student management system</li>
                            <li>Automated attendance tracking tools</li>
                            <li>Customizable attendance reports</li>
                            <li>System configuration and settings</li>
                            <li>Communication tools for staff and parents</li>
                        </ul>
                    </div>
                    <div style="margin: 20px 0;">
                        <p><strong>Quick Start Guide:</strong></p>
                        <ol>
                            <li>Log in at: https://attendance.yoventa.com</li>
                            <li>Change your password</li>
                            <li>Complete your school profile</li>
                            <li>Add your staff members</li>
                            <li>Configure attendance policies</li>
                        </ol>
                    </div>
                    <p>Need help? Contact our support team:</p>
                    <ul>
                        <li>Email: support@yoventa.com</li>
                        <li>Phone: +1-XXX-XXX-XXXX</li>
                        <li>Support Hours: Monday-Friday, 8 AM - 6 PM</li>
                    </ul>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa Attendance Management System Team</strong></p>
                </div>
            </body>
        </html>
        """
        return await self.send_email_with_retry([email], subject, body)

    async def send_teacher_credentials(self, email: str, name: str, password: str, school_name: str):
        """Send login credentials to newly registered teacher"""
        subject = "Welcome to Yoventa Attendance Management System - Teacher Account Created"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Welcome to Yoventa Attendance Management System</h2>
                    <p>Dear {name},</p>
                    <p>Your teacher account has been created for {school_name} in the Yoventa Attendance Management System.</p>
                    <div style="background-color: #f7fafc; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="font-weight: bold;">Your login credentials are:</p>
                        <ul>
                            <li>Email: {email}</li>
                            <li>Password: {password}</li>
                        </ul>
                    </div>
                    <p style="color: #e53e3e;">For security reasons, please change your password after your first login.</p>
                    <div style="margin: 20px 0;">
                        <p><strong>With Yoventa, you can:</strong></p>
                        <ul>
                            <li>Mark your daily attendance with biometric or QR code options</li>
                            <li>Record and manage student attendance for your classes</li>
                            <li>Generate attendance reports and analytics</li>
                            <li>View your attendance history and statistics</li>
                            <li>Request and manage leave applications</li>
                            <li>Communicate with administration and parents</li>
                        </ul>
                    </div>
                    <div style="margin: 20px 0;">
                        <p><strong>Getting Started:</strong></p>
                        <ol>
                            <li>Access the system at: https://attendance.yoventa.com</li>
                            <li>Log in with your credentials</li>
                            <li>Change your default password</li>
                            <li>Complete your profile information</li>
                            <li>Download our mobile app for quick attendance marking</li>
                        </ol>
                    </div>
                    <p>For assistance, contact our support team:</p>
                    <ul>
                        <li>Email: support@yoventa.com</li>
                        <li>Phone: +1-XXX-XXX-XXXX</li>
                        <li>Support Hours: Monday-Friday, 8 AM - 6 PM</li>
                    </ul>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa Attendance Management System Team</strong></p>
                </div>
            </body>
        </html>
        """
        return await self.send_email_with_retry([email], subject, body)

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
        subject = f"Welcome to Yoventa Attendance Management System - Parent Portal Access"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Welcome to Yoventa Attendance Management System</h2>
                    <p>Dear {name},</p>
                    <p>Welcome to the Yoventa Parent Portal. Your account has been created to monitor {student_name}'s attendance at {school_name}.</p>
                    <div style="background-color: #f7fafc; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="font-weight: bold;">Your login credentials are:</p>
                        <ul>
                            <li>Email: {email}</li>
                            <li>Password: {password}</li>
                        </ul>
                    </div>
                    <p><strong>Access the parent portal here:</strong> <a href="{access_link}" style="color: #2b6cb0;">Yoventa Parent Portal</a></p>
                    <div style="margin: 20px 0;">
                        <p><strong>With Yoventa Parent Portal, you can:</strong></p>
                        <ul>
                            <li>Monitor your child's real-time attendance status</li>
                            <li>Receive instant notifications for absences</li>
                            <li>View detailed attendance reports and analytics</li>
                            <li>Submit leave applications and documentation</li>
                            <li>Communicate directly with teachers</li>
                            <li>Set up attendance alerts and notifications</li>
                        </ul>
                    </div>
                    <div style="margin: 20px 0;">
                        <p><strong>Getting Started:</strong></p>
                        <ol>
                            <li>Click on the portal access link above</li>
                            <li>Log in with your credentials</li>
                            <li>Change your password</li>
                            <li>Set up notification preferences</li>
                            <li>Download our mobile app for on-the-go access</li>
                        </ol>
                    </div>
                    <p style="color: #e53e3e;">For security reasons, please change your password after your first login.</p>
                    <p>Need assistance? Contact our support team:</p>
                    <ul>
                        <li>Email: support@yoventa.com</li>
                        <li>Phone: +1-XXX-XXX-XXXX</li>
                        <li>Support Hours: Monday-Friday, 8 AM - 6 PM</li>
                    </ul>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa Attendance Management System Team</strong></p>
                </div>
            </body>
        </html>
        """
        return await self.send_email_with_retry([email], subject, body)

    async def send_teacher_late_arrival(self, teacher_email: str, teacher_name: str, arrival_time: time):
        """Send notification when a teacher arrives late"""
        subject = "Yoventa Attendance Notification - Late Arrival Recording"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Attendance Notification</h2>
                    <p>Dear {teacher_name},</p>
                    <p>This is an automated notification from Yoventa Attendance Management System.</p>
                    <div style="background-color: #fff3f3; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Late Arrival Record:</strong></p>
                        <ul>
                            <li>Date: {datetime.now().strftime('%B %d, %Y')}</li>
                            <li>Arrival Time: {arrival_time.strftime('%I:%M %p')}</li>
                        </ul>
                    </div>
                    <p>Please note:</p>
                    <ul>
                        <li>This arrival has been recorded in the Yoventa system</li>
                        <li>The record will be included in your monthly attendance report</li>
                        <li>Multiple late arrivals may require administrative review</li>
                    </ul>
                    <p>If you believe this is an error or have a valid reason for the late arrival, please:</p>
                    <ol>
                        <li>Log into your Yoventa account</li>
                        <li>Navigate to 'Attendance Records'</li>
                        <li>Submit a justification for review</li>
                    </ol>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa Attendance Management System</strong></p>
                </div>
            </body>
        </html>
        """
        return await self.send_email_with_retry([teacher_email], subject, body)

    async def send_absence_notification(
        self,
        teacher_email: str,
        teacher_name: str,
        absence_date: datetime,
        school_name: str
    ):
        """Send notification for teacher absence"""
        subject = "Yoventa Attendance Notification - Absence Record"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Absence Notification</h2>
                    <p>Dear {teacher_name},</p>
                    <p>Your absence has been recorded in the Yoventa Attendance Management System.</p>
                    <div style="background-color: #fff3f3; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Absence Details:</strong></p>
                        <ul>
                            <li>School: {school_name}</li>
                            <li>Date: {absence_date.strftime('%B %d, %Y')}</li>
                            <li>Status: Unexcused Absence</li>
                        </ul>
                    </div>
                    <p>Required Actions:</p>
                    <ol>
                        <li>Log into your Yoventa account</li>
                        <li>Submit an absence justification</li>
                        <li>Upload any supporting documentation</li>
                    </ol>
                    <p>Please complete these actions within 48 hours.</p>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa Attendance Management System</strong></p>
                </div>
            </body>
        </html>
        """
        return await self.send_email_with_retry([teacher_email], subject, body)

    async def send_attendance_summary(
        self,
        email: str,
        name: str,
        summary_data: dict,
        month: str,
        year: int,
        school_name: str
    ):
        """Send monthly attendance summary"""
        subject = f"Yoventa Monthly Attendance Summary - {month} {year}"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Monthly Attendance Summary</h2>
                    <p>Dear {name},</p>
                    <p>Here is your attendance summary for {month} {year} at {school_name}.</p>
                    <div style="background-color: #f7fafc; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Attendance Statistics:</strong></p>
                        <ul>
                            <li>Total Working Days: {summary_data['total_days']}</li>
                            <li>Present Days: {summary_data['present_days']}</li>
                            <li>Absent Days: {summary_data['absent_days']}</li>
                            <li>Late Arrivals: {summary_data['late_arrivals']}</li>
                            <li>Attendance Rate: {summary_data['attendance_rate']}%</li>
                        </ul>
                    </div>
                    <p>For detailed attendance records, please log into your Yoventa account.</p>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa Attendance Management System</strong></p>
                </div>
            </body>
        </html>
        """
        return await self.send_email_with_retry([email], subject, body)

    async def send_leave_application_status(
        self,
        email: str,
        name: str,
        leave_data: dict,
        school_name: str
    ):
        """Send leave application status update"""
        subject = "Yoventa Leave Application Status Update"
        status_color = "#22c55e" if leave_data['status'] == 'approved' else "#ef4444"
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5282;">Leave Application Update</h2>
                    <p>Dear {name},</p>
                    <p>Your leave application has been reviewed by the administration at {school_name}.</p>
                    <div style="background-color: #f7fafc; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Application Details:</strong></p>
                        <ul>
                            <li>Leave Type: {leave_data['type']}</li>
                            <li>From: {leave_data['start_date']}</li>
                            <li>To: {leave_data['end_date']}</li>
                            <li>Status: <span style="color: {status_color};">{leave_data['status'].upper()}</span></li>
                        </ul>
                        <p><strong>Reviewer Comments:</strong></p>
                        <p>{leave_data['comments']}</p>
                    </div>
                    <p>You can view the complete details in your Yoventa account.</p>
                    <hr style="border: 1px solid #edf2f7; margin: 20px 0;">
                    <p>Best regards,</p>
                    <p><strong>Yoventa Attendance Management System</strong></p>
                </div>
            </body>
        </html>
        """
        return await self.send_email_with_retry([email], subject, body)

async def test_email_service():
    """Test the email service with registration emails"""
    try:
        logger.info("Starting email service test")
        email_service = EmailService()
        test_email = os.getenv('TEST_EMAIL')
        
        if not test_email:
            raise ValueError("No test email address configured")
        
        # Test cases for various email notifications
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
            ),
            email_service.send_attendance_summary(
                test_email,
                "Test User",
                {
                    "total_days": 22,
                    "present_days": 20,
                    "absent_days": 2,
                    "late_arrivals": 1,
                    "attendance_rate": 90.91
                },
                "December",
                2024,
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
    asyncio.run(test_email_service())