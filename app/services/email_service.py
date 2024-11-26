import asyncio
from typing import List
from pydantic import EmailStr
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from datetime import datetime, time

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME="mikailismail260@gmail.com",
    MAIL_PASSWORD="bblm rlde aapg ydsp",
    MAIL_FROM="mikailismail260@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

class EmailService:
    def __init__(self):
        self.fastmail = FastMail(conf)

    async def send_email(self, recipients: List[str], subject: str, body: str):
        """Base method to send emails"""
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype="html"
        )
        try:
            await self.fastmail.send_message(message)
            print(f"✓ Email sent successfully to {', '.join(recipients)}")
            return True
        except Exception as e:
            print(f"✗ Failed to send email: {str(e)}")
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

    async def send_teacher_absence_alert(self, teacher_email: str, teacher_name: str, absence_date: datetime):
        """Send notification for teacher absence"""
        subject = "Absence Recording Confirmation"
        body = f"""
        <html>
            <body>
                <h2>Absence Recording</h2>
                <p>Dear {teacher_name},</p>
                <p>This email confirms your absence has been recorded for {absence_date.strftime('%B %d, %Y')}.</p>
                <p>If this was recorded in error, please contact the school administration immediately.</p>
                <br>
                <p>Best regards,</p>
                <p>School Administration</p>
            </body>
        </html>
        """
        return await self.send_email([teacher_email], subject, body)

    async def send_parent_attendance_notification(
        self, 
        parent_email: str, 
        student_name: str, 
        status: str, 
        timestamp: datetime
    ):
        """Send attendance notification to parents"""
        subject = f"Student Attendance Update - {student_name}"
        status_message = "arrived at" if status == "check_in" else "left"
        
        body = f"""
        <html>
            <body>
                <h2>Student Attendance Update</h2>
                <p>Dear Parent/Guardian,</p>
                <p>This is to inform you that {student_name} has {status_message} school at {timestamp.strftime('%I:%M %p')}.</p>
                <p>Date: {timestamp.strftime('%B %d, %Y')}</p>
                <br>
                <p>Best regards,</p>
                <p>School Administration</p>
            </body>
        </html>
        """
        return await self.send_email([parent_email], subject, body)

    async def send_parent_absence_notification(
        self, 
        parent_email: str, 
        student_name: str, 
        absence_date: datetime
    ):
        """Send absence notification to parents"""
        subject = f"Student Absence Notification - {student_name}"
        body = f"""
        <html>
            <body>
                <h2>Student Absence Notification</h2>
                <p>Dear Parent/Guardian,</p>
                <p>This email is to inform you that {student_name} was marked absent on {absence_date.strftime('%B %d, %Y')}.</p>
                <p>If you believe this is an error, please contact the school administration.</p>
                <br>
                <p>Best regards,</p>
                <p>School Administration</p>
            </body>
        </html>
        """
        return await self.send_email([parent_email], subject, body)

    async def send_admin_daily_report(
        self,
        admin_email: str,
        date: datetime,
        total_present: int,
        total_absent: int,
        late_arrivals: int
    ):
        """Send daily attendance summary to admin"""
        subject = f"Daily Attendance Summary - {date.strftime('%B %d, %Y')}"
        body = f"""
        <html>
            <body>
                <h2>Daily Attendance Summary</h2>
                <p>Here is the attendance summary for {date.strftime('%B %d, %Y')}:</p>
                <ul>
                    <li>Total Students Present: {total_present}</li>
                    <li>Total Students Absent: {total_absent}</li>
                    <li>Late Arrivals: {late_arrivals}</li>
                </ul>
                <p>Attendance Rate: {(total_present/(total_present + total_absent) * 100):.2f}%</p>
                <br>
                <p>Best regards,</p>
                <p>Attendance Management System</p>
            </body>
        </html>
        """
        return await self.send_email([admin_email], subject, body)

# Test function
async def test_email_service():
    email_service = EmailService()
    current_time = datetime.now()
    
    # Test different email scenarios
    test_cases = [
        # Test teacher late arrival
        email_service.send_teacher_late_arrival(
            "zeiyhassan52@gmail.com",
            "Mr. Hassan",
            current_time.time()
        ),
        
        # Test teacher absence
        email_service.send_teacher_absence_alert(
            "zeiyhassan52@gmail.com",
            "Mr. Hassan",
            current_time
        ),
        
        # Test student check-in notification
        email_service.send_parent_attendance_notification(
            "zeiyhassan52@gmail.com",
            "Ahmed Hassan",
            "check_in",
            current_time
        ),
        
        # Test student absence notification
        email_service.send_parent_absence_notification(
            "zeiyhassan52@gmail.com",
            "Ahmed Hassan",
            current_time
        ),
        
        # Test admin daily report
        email_service.send_admin_daily_report(
            "zeiyhassan52@gmail.com",
            current_time,
            450,
            50,
            10
        )
    ]
    
    # Run all tests
    results = await asyncio.gather(*test_cases)
    
    # Print results
    print("\nEmail Test Results:")
    print("✓ All test emails sent successfully!" if all(results) else "✗ Some emails failed to send")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_email_service())