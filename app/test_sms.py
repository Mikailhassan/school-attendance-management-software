import asyncio
import os
from dotenv import load_dotenv
import logging
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
import aiohttp
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
    PIN_ATTEMPTS: int = Field(10, description="Number of PIN verification attempts")
    PIN_TTL: str = Field("15m", description="PIN time to live")
    VERIFY_PIN_LIMIT: str = Field("1/3s", description="PIN verification rate limit")
    SEND_PIN_APP_LIMIT: str = Field("100/1d", description="Application-wide PIN sending limit")
    SEND_PIN_NUMBER_LIMIT: str = Field("10/1d", description="Per phone number PIN sending limit")

    class Config:
        env_prefix = "INFOBIP_"

class SMSMessage(BaseModel):
    """SMS message model"""
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

                if message.notify_url:
                    payload["messages"][0]["notifyUrl"] = message.notify_url
                    payload["messages"][0]["notifyContentType"] = message.notify_content_type or "application/json"
                
                if message.callback_data:
                    payload["messages"][0]["callbackData"] = message.callback_data

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

async def test_sms_service():
    # Load environment variables
    load_dotenv()
    
    # Create configuration
    config = InfobipConfig(
        BASE_URL=os.getenv("INFOBIP_BASE_URL"),
        API_KEY=os.getenv("INFOBIP_API_KEY"),
        SENDER_ID=os.getenv("INFOBIP_SENDER_ID", "Youventa")
    )
    
    # Initialize SMS service
    sms_service = InfobipSMSService(config)
    
    # Test sending a regular SMS
    try:

        test_message = SMSMessage(
            to="+254723423256",
            text="Hello! This is a test message from Yoventa attendance management software SMS Service. fuck you oscar , from your truly Mikail Hassan",
            sender_id="Yoventa"
        )
        
        logger.info("Sending test SMS...")
        response = await sms_service.send_sms(test_message)
        logger.info(f"SMS Response: {response}")
        
    except Exception as e:
        logger.error(f"Error during SMS test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_sms_service())