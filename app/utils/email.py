# utils/email.py
from flask_mail import Mail, Message
from flask import Flask

# Configuration for Flask-Mail
app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'youremail@gmail.com'
app.config['MAIL_PASSWORD'] = 'yourpassword'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

def send_email(recipient: str, subject: str, body: str):
    """
    Send an email to the specified recipient.
    """
    with app.app_context():
        msg = Message(subject, sender="noreply@school-system.com", recipients=[recipient])
        msg.body = body
        mail.send(msg)
        print(f"Email sent to {recipient}: {subject}")
