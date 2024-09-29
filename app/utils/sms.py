# utils/sms.py

def send_sms(phone_number: str, message: str):
    """
    Simulate sending an SMS to a phone number.
    In reality, this would connect to an SMS provider such as Twilio.
    """
    # For demonstration purposes, we are just printing the SMS details
    print(f"Sending SMS to {phone_number}: {message}")
    # Here, you would integrate with Twilio or another provider's API
    return True
