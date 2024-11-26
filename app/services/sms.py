# app/services/sms.py
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional
import aiohttp
import logging
from datetime import datetime
import re
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InfobipConfig(BaseModel):
    """Infobip configuration settings"""
    BASE_URL: str = Field(..., description="Infobip API base URL")
    API_KEY: str = Field(..., description="Infobip API key")
    SENDER_ID: str = Field("Youventa", description="Default sender ID")

    class Config:
        env_prefix = "INFOBIP_"

class SMSMessage(BaseModel):
    """SMS message model"""
    to: str
    text: str
    sender_id: Optional[str] = None

    @validator('to')
    def validate_phone_number(cls, v):
        if not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError("Invalid phone number format. Must be E.164 format (+1234567890)")
        return v

class SMSResponse(BaseModel):
    """SMS response model"""
    message_id: Optional[str]
    status: str
    to: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None

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
        """Send SMS using Infobip API"""
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