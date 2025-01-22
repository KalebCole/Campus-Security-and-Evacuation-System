# server/utils/notifications.py
import requests
from models.notifications import Notification
from twilio.rest import Client
from config import Config

# Function to send a notification

# TODO: fix the endpoint to use the hashed topic instead of the topic name


def send_notification(notification: Notification, topic: str = "facial-recognition-CSS-testing"):
    # Sending notification via POST request
    response = requests.post(
        f"https://ntfy.sh/{topic}",
        data=str(notification),
        headers={"Markdown": "yes"}
    )

    if response.status_code == 200:
        print("Notification sent successfully!")
    else:
        print("Failed to send notification.")


def send_sms_notification(notification: Notification, phone_number: str = '+18777804236'):
    """
    Send an SMS notification.

    Args:
        notification (Notification): The notification to send.
        phone_number (str): The phone number to send the notification to.
    """
    # Sending notification via SMS
    client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=Config.TWILIO_PHONE_NUMBER,
        body='Hello EE481 Team! ' + str(notification),
        to='+18777804236'
    )
    print(message.sid)
