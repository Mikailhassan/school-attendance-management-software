import asyncio
from typing import Dict, Any
from pydantic import BaseModel, validator
import re

class SMSConfig(BaseModel):
    TWILIO_ACCOUNT_SID: str = "your_account_sid"
    TWILIO_AUTH_TOKEN: str = "your_auth_token"
    TWILIO_PHONE_NUMBER: str = "+2544567890"

    class Config:
        env_file = ".env"

class SMS(BaseModel):
    to: str
    body: str

    @validator('to')
    def validate_phone_number(cls, v):
        if not re.match(r'^\+?1?\d{9,15}$', v):
            raise ValueError("Invalid phone number format")
        return v

async def send_sms(sms: SMS, config: SMSConfig = SMSConfig()) -> Dict[str, Any]:
    """
    Simulate sending an SMS to a phone number.
    In reality, this would connect to an SMS provider such as Twilio.
    """
    try:
        # Simulate API call delay
        await asyncio.sleep(1)
        
        # For demonstration purposes, we are just printing the SMS details
        print(f"Sending SMS to {sms.to}: {sms.body}")
        print(f"Using Twilio account: {config.TWILIO_ACCOUNT_SID}")
        
        # Here, you would integrate with Twilio or another provider's API
        # For example:
        # client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=sms.body,
        #     from_=config.TWILIO_PHONE_NUMBER,
        #     to=sms.to
        # )
        # return {"status": "sent", "message_id": message.sid}
        
        return {"status": "sent", "message": "SMS sent successfully"}
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")
        return {"status": "failed", "error": str(e)}

async def send_school_welcome_sms(school_phone: str, school_name: str):
    """Send a welcome SMS to a newly registered school"""
    sms = SMS(
        to=school_phone,
        body=f"Welcome, {school_name}! Thank you for joining Youventa Attendance Management System. We're excited to help you manage your school's attendance efficiently."
    )
    return await send_sms(sms)

async def send_student_check_notification_sms(parent_phone: str, student_name: str, check_type: str):
    """Send a notification SMS to parents when their child checks in or out"""
    action = "checked in to" if check_type == "check_in" else "checked out of"
    sms = SMS(
        to=parent_phone,
        body=f"This is to inform you that {student_name} has successfully {action} school."
    )
    return await send_sms(sms)

async def send_teacher_reminder_sms(teacher_phone: str, teacher_name: str, missing_action: str):
    """Send a reminder SMS to teachers if they forget to check in or out"""
    sms = SMS(
        to=teacher_phone,
        body=f"Dear {teacher_name}, This is a friendly reminder that you have not {missing_action} today. Please remember to mark your attendance regularly."
    )
    return await send_sms(sms)

# Example usage
# await send_school_welcome_sms("+1234567890", "Sunshine Elementary")
# await send_student_check_notification_sms("+1234567890", "John Doe", "check_in")
# await send_teacher_reminder_sms("+1234567890", "Ms. Smith", "checked in")