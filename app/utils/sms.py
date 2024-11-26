from typing import Dict, Any, Optional, Union
import json
from datetime import datetime
from pydantic import BaseModel, Field, validator
import logging
from fastapi import HTTPException
import re
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Models
class InfobipConfig(BaseModel):
    BASE_URL: str = Field(..., description="Infobip API base URL")
    API_KEY: str = Field(..., description="Infobip API key")
    SENDER_ID: str = Field("Youventa", description="Default sender ID")
    PIN_ATTEMPTS: int = Field(10, description="Number of PIN verification attempts")
    PIN_TTL: str = Field("15m", description="PIN time to live")
    VERIFY_PIN_LIMIT: str = Field("1/3s", description="PIN verification rate limit")
    SEND_PIN_APP_LIMIT: str = Field("100/1d", description="Application-wide PIN sending limit")
    SEND_PIN_NUMBER_LIMIT: str = Field("10/1d", description="Per phone number PIN sending limit")

    class Config:
        env_prefix = "INFOBIP_"

class SMS2FAApplication(BaseModel):
    name: str
    enabled: bool = True
    configuration: Dict[str, Any]

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

# Infobip SMS Service
class InfobipSMSService:
    def __init__(self, config: InfobipConfig):
        self.config = config
        self.headers = {
            'Authorization': f'App {self.config.API_KEY}',
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

# Utility Functions for Notifications
async def send_student_attendance_notification(
    service: InfobipSMSService,
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
    return await service.send_sms(message)

async def send_teacher_reminder(
    service: InfobipSMSService,
    teacher_phone: str,
    teacher_name: str,
    missing_action: str
) -> SMSResponse:
    """Send reminder to teachers."""
    message = SMSMessage(
        to=teacher_phone,
        text=f"Reminder: Dear {teacher_name}, you have not {missing_action} today. Please mark your attendance."
    )
    return await service.send_sms(message)

async def send_school_announcement(
    service: InfobipSMSService,
    recipients: list,
    announcement: str
) -> Dict[str, SMSResponse]:
    """Send school-wide announcements."""
    responses = {}
    for recipient in recipients:
        message = SMSMessage(
            to=recipient,
            text=f"Announcement: {announcement}"
        )
        responses[recipient] = await service.send_sms(message)
    return responses

# Example Integration with FastAPI
"""
from fastapi import FastAPI, Depends
from functools import lru_cache

app = FastAPI()

@lru_cache()
def get_infobip_config() -> InfobipConfig:
    return InfobipConfig(
        BASE_URL="e5dkp3.api.infobip.com",
        API_KEY="YOUR_API_KEY"
    )

@lru_cache()
def get_sms_service(config: InfobipConfig = Depends(get_infobip_config)) -> InfobipSMSService:
    return InfobipSMSService(config)

@app.post("/send-sms")
async def send_sms(
    message: SMSMessage,
    sms_service: InfobipSMSService = Depends(get_sms_service)
):
    return await sms_service.send_sms(message)

@app.post("/send-student-attendance-notification")
async def send_student_notification(
    parent_phone: str,
    student_name: str,
    check_type: str,
    sms_service: InfobipSMSService = Depends(get_sms_service)
):
    return await send_student_attendance_notification(sms_service, parent_phone, student_name, check_type)

@app.post("/send-teacher-reminder")
async def send_teacher_reminder_api(
    teacher_phone: str,
    teacher_name: str,
    missing_action: str,
    sms_service: InfobipSMSService = Depends(get_sms_service)
):
    return await send_teacher_reminder(sms_service, teacher_phone, teacher_name, missing_action)

@app.post("/send-school-announcement")
async def send_announcement(
    recipients: list,
    announcement: str,
    sms_service: InfobipSMSService = Depends(get_sms_service)
):
    return await send_school_announcement(sms_service, recipients, announcement)
"""
