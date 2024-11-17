# server/utils/notifications.py
import requests
from models.notifications import Notification

# Function to send a notification

# TODO: fix the endpoint to use the hashed topic instead of the topic name
def send_notification(notification: Notification, topic: str = "facial-recognition-CSS-testing"):
    # Sending notification via POST request
    response = requests.post(
        f"https://ntfy.sh/{topic}",
        json={"message": str(notification)},  # Use the __str__ method
        headers={"Markdown": "yes"}
    )

    if response.status_code == 200:
        print("Notification sent successfully!")
    else:
        print("Failed to send notification.")
