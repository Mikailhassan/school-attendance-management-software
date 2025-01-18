from typing import Dict, Any, Optional, List
import json
from datetime import datetime
from pydantic import BaseModel, Field, validator
import logging
import re
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Models
class SMSConfig(BaseModel):
    """Configuration model for SMS service that handles both Infobip and general settings"""
    provider: str = Field(..., description="SMS provider name")
    enabled: bool = Field(..., description="Whether SMS service is enabled")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key")
    sender_id: str = Field(..., description="Sender ID")
    rate_limits: dict = Field(..., description="Rate limiting configuration")


# Message and Response Models
class SMSMessage(BaseModel):
    to: str
    text: str
    sender_id: Optional[str] = None
    notify_url: Optional[str] = None
    notify_content_type: Optional[str] = None
    callback_data: Optional[str] = None

    @validator('to')
    def validate_phone_number(cls, v):
        if not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError("Invalid phone number format. Must be E.164 format (+1234567890)")
        return v

class SMSResponse(BaseModel):
    message_id: Optional[str]
    status: str
    to: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None

# SMS Service Class
class SMSService:
    def __init__(self, config: dict):
        self.config = SMSConfig(**config)
        self.headers = {
            'Authorization': f'App {self.config.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_sms(self, message: SMSMessage) -> SMSResponse:
        """Send SMS using Infobip API."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "messages": [{
                        "from": message.sender_id or self.config.SENDER_ID,
                        "destinations": [{"to": message.to}],
                        "text": message.text,
                    }]
                }

                async with session.post(
                    f"https://{self.config.BASE_URL}/sms/2/text/advanced",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_msg = await response.text()
                        logger.error(f"Failed to send SMS: {error_msg}")
                        return SMSResponse(
                            status="failed",
                            to=message.to,
                            error=error_msg
                        )

                    result = await response.json()
                    message_id = result.get("messages", [{}])[0].get("messageId")

                    return SMSResponse(
                        message_id=message_id,
                        status="sent",
                        to=message.to
                    )

        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return SMSResponse(
                status="failed",
                to=message.to,
                error=str(e)
            )

    async def send_student_attendance_notification(
        self,
        parent_phone: str,
        student_name: str,
        check_type: str,
        timestamp: datetime = None
    ) -> SMSResponse:
        """Send attendance notification to parents."""
        action = "checked in to" if check_type == "check_in" else "checked out of"
        timestamp_str = timestamp.strftime("%I:%M %p") if timestamp else datetime.now().strftime("%I:%M %p")

        message = SMSMessage(
            to=parent_phone,
            text=f"Notification: {student_name} has {action} school at {timestamp_str}."
        )
        return await self.send_sms(message)

    async def send_teacher_reminder(
        self,
        teacher_phone: str,
        teacher_name: str,
        missing_action: str
    ) -> SMSResponse:
        """Send reminder to teachers."""
        message = SMSMessage(
            to=teacher_phone,
            text=f"Reminder: Dear {teacher_name}, you have not {missing_action} today. Please mark your attendance."
        )
        return await self.send_sms(message)

    async def send_school_announcement(
        self,
        recipients: List[str],
        announcement: str
    ) -> Dict[str, SMSResponse]:
        """Send school-wide announcements."""
        responses = {}
        for recipient in recipients:
            message = SMSMessage(
                to=recipient,
                text=f"Announcement: {announcement}"
            )
            responses[recipient] = await self.send_sms(message)
        return responses
