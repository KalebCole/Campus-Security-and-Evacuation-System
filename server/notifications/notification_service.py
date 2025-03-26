import json
from data.notification import Notification, NotificationType, SeverityLevel
import requests
from twilio.rest import Client
from app_config import Config


class NotificationService:
    def __init__(self, json_db_path="notifications.json"):
        self.json_db_path = json_db_path

        # Define message templates for each event type, for both channels.
        # The placeholders (e.g. {timestamp}, {image_url}) will be populated at runtime.
        # TODO: how will they be populated? Will they be passed in as arguments to the send method?
        # TODO: fix the case where i am testing rfid recognized and the image is not found
        # solve this by adding a default image url
        self.event_templates = {
            # === RFID Templates ===
            NotificationType.RFID_NOT_FOUND: {
                "ntfy": "## RFID Not Found\n**Timestamp:** {timestamp}\n",
                "sms": "RFID not found at {timestamp}.",
            },
            NotificationType.RFID_NOT_RECOGNIZED: {
                "ntfy": "## RFID Not Recognized\nRFID was not recognized at {timestamp}",
                "sms": "RFID not recognized at {timestamp}",
            },
            NotificationType.RFID_RECOGNIZED: {
                "ntfy": ("## RFID Recognized\n"
                         "**Name:** {name}\n"
                         "**Role:** {role}\n"
                         "**Employee Image:** ![Employee Image]({employee_image_url})"),
                "sms": "RFID recognized: {name} ({role})",
            },
            # === Face Templates ===
            NotificationType.FACE_NOT_RECOGNIZED: {
                "ntfy": ("## Face Not Recognized\n**Name:** {name}\n**Role:** {role}\n"
                         "**DB Image:** ![DB Image]({db_image_url})\n"
                         "**Captured Image:** ![Captured Image]({captured_image_url})"),
                "sms": "Face not recognized: {name} ({role}).",
            },
            NotificationType.FACE_NOT_FOUND: {
                "ntfy": "## Face Not Found\nNo face found at {timestamp}",
                "sms": "No face found at {timestamp}",
            },
            NotificationType.FACE_RECOGNIZED: {
                "ntfy": ("## Face Recognized\n**Name:** {name}\n**Role:** {role}\n"
                         "**Employee Image:** ![Employee Image]({employee_image_url})\n"
                         "**Captured Face:** ![Captured Face]({captured_face_url})"),
                "sms": "Face recognized: {name} ({role})",
            },
            # === Access Templates ===
            NotificationType.ACCESS_GRANTED: {
                "ntfy": "## Access Granted\n**Time**:{timestamp}\n**Name:** {name}\n**Role:** {role}\n![Image]({image_url})",
                "sms": "Access granted for {name} ({role})",
            },
            NotificationType.MULTIPLE_FAILED_ATTEMPTS: {
                "ntfy": "## Multiple Failed Attempts\n**RFID Tags:** {rfid_tags}\n**Count:** {count}",
                "sms": "Multiple failed attempts: {rfid_tags} (Total: {count})",
            },
        }

        # Map each event type to the channels it should use
        self.channel_mapping = {
            NotificationType.RFID_NOT_FOUND: ["ntfy"],
            NotificationType.FACE_NOT_FOUND: ["ntfy"],
            NotificationType.FACE_NOT_RECOGNIZED: ["ntfy", "sms"],
            NotificationType.RFID_NOT_RECOGNIZED: ["ntfy", "sms"],
            NotificationType.FACE_RECOGNIZED: ["ntfy"],
            NotificationType.RFID_RECOGNIZED: ["ntfy"],
            NotificationType.ACCESS_GRANTED: ["ntfy", "sms"],
            NotificationType.MULTIPLE_FAILED_ATTEMPTS: ["ntfy", "sms"],
        }

    def send(self, event_type: NotificationType, data: dict) -> Notification:
        """
        Central method to send a notification.

        Args:
            event_type (NotificationType): The type of event.
            data (dict): Dynamic data that will populate the message template.
                         Expected keys depend on the event (e.g. timestamp, image_url, employee_info, etc.)

        Returns:
            Notification: The notification object created and persisted.

        Usage:
            notification_service = NotificationService()
            notification = notification_service.send(
                NotificationType.RFID_NOT_FOUND,
                {
                    "timestamp": "2021-06-01 12:00:00",
                    "image_url": "https://example.com/image.jpg", 
                }
            )        
        """
        # Retrieve the template for this event type.
        template = self.event_templates.get(event_type)
        if not template:
            print(f"No template defined for event type: {event_type}")
            return None

        # For each channel in the mapping, generate the message.
        messages = {}
        for channel in self.channel_mapping.get(event_type, []):
            try:
                message = template[channel].format(**data)
                messages[channel] = message
            except KeyError as e:
                print(f"Missing placeholder {e} in data for event {event_type}")
                messages[channel] = f"Error formatting message: missing {e}"

        # Create a Notification object.
        # We'll use the ntfy version as the primary message.
        notification = Notification(
            event_type=event_type,
            severity=data.get("severity", SeverityLevel.INFO),
            session_id=data.get("session_id"),
            user_id=data.get("user_id"),
            message=messages.get("ntfy"),
            image_url=data.get("image_url"),
            additional_data=data,
        )

        # Persist the notification to our JSON database.
        self.persist_notification(notification)

        # Send the notifications over each configured channel.
        for channel, message in messages.items():
            if channel == "ntfy":
                self.send_ntfy_notification(message)
            elif channel == "sms":
                phone_number = data.get(
                    "phone_number", Config.TWILIO_PHONE_NUMBER)
                self.send_sms_notification(
                    message, phone_number, mock=Config.MOCK_VALUE)

        return notification
    # TODO: fix the topic to be dynamic based on the event type. should we have different topics for each event type?

    def send_ntfy_notification(self, message: str, topic: str = "facial-recognition-CSS-testing"):
        response = requests.post(
            f"https://ntfy.sh/{topic}",
            data=message,
            headers={"Markdown": "yes"}
        )
        if response.status_code == 200:
            print("ntfy notification sent successfully.")
        else:
            print("Failed to send ntfy notification.")

    def send_sms_notification(self, message: str, phone_number: str, mock=False):
        if mock:
            print(f"[Mock SMS] Would have sent SMS to {
                  phone_number} with message: {message}")
            return
        try:
            client = Client(Config.TWILIO_ACCOUNT_SID,
                            Config.TWILIO_AUTH_TOKEN)
            msg = client.messages.create(
                from_=Config.TWILIO_PHONE_NUMBER,
                body=message,
                to=phone_number
            )
            print("SMS sent successfully:", msg.sid)
        except Exception as e:
            print("Failed to send SMS:", e)

    def persist_notification(self, notification: Notification):
        # Load existing notifications from the JSON file.
        try:
            with open(self.json_db_path, "r") as f:
                notifications = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            notifications = []

        notifications.append(notification.to_dict())

        with open(self.json_db_path, "w") as f:
            json.dump(notifications, f, indent=4)
        print("Notification persisted.")

    # Methods to update or delete notifications from the JSON "database"
    def mark_as_read(self, notification_id: str):
        try:
            with open(self.json_db_path, "r") as f:
                notifications = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            notifications = []

        for notif in notifications:
            if notif["id"] == notification_id:
                notif["status"] = "Read"
                break

        with open(self.json_db_path, "w") as f:
            json.dump(notifications, f, indent=4)
        print("Notification marked as read.")

    def delete_notification(self, notification_id: str):
        try:
            with open(self.json_db_path, "r") as f:
                notifications = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            notifications = []

        notifications = [
            notif for notif in notifications if notif["id"] != notification_id]

        with open(self.json_db_path, "w") as f:
            json.dump(notifications, f, indent=4)
        print("Notification deleted.")
