import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_smtp_587():
    sender_email = "mikailismail260@gmail.com"
    password = "ebpkdhyzmujkiaf"
    receiver_email = "omarmahat702@gmail.com"
    
    print("Setting up message...")
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "SMTP Test"
    
    text = "This is a test email using port 587 with STARTTLS"
    message.attach(MIMEText(text, "plain"))

    try:
        print("Connecting to SMTP server...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        print("Connected! Sending EHLO...")
        server.ehlo()
        print("Starting TLS...")
        server.starttls(context=ssl.create_default_context())
        print("Logging in...")
        server.login(sender_email, password)
        print("Sending mail...")
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")
        server.quit()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    print("Starting SMTP test using port 587...")
    test_smtp_587()