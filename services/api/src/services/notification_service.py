import logging
import requests
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Use relative imports
from ..core.config import Config
from ..models.notification import Notification, SeverityLevel

logger = logging.getLogger(__name__)


class NotificationService:
    """Service responsible for dispatching notifications via various channels."""

    def __init__(self):
        """Initialize the notification service and its clients based on config."""
        self.notifications_enabled = Config.ENABLE_NOTIFICATIONS
        self.twilio_client = None
        self.twilio_from_number = Config.TWILIO_PHONE_NUMBER
        self.sms_recipients = Config.NOTIFICATION_PHONE_NUMBERS
        self.ntfy_topic = Config.NTFY_TOPIC

        if not self.notifications_enabled:
            logger.info("Notifications are disabled via configuration.")
            return

        # Initialize Twilio Client
        if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN and self.twilio_from_number:
            try:
                self.twilio_client = Client(
                    Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
                # Test connection by fetching account details (optional, but good practice)
                self.twilio_client.api.accounts(
                    Config.TWILIO_ACCOUNT_SID).fetch()
                logger.info("Twilio client initialized successfully.")
            except TwilioRestException as e:
                logger.error(
                    f"Failed to initialize Twilio client: {e} - Check SID, Token, and connectivity.")
                self.twilio_client = None  # Ensure client is None if init fails
            except Exception as e:
                logger.error(
                    f"Unexpected error initializing Twilio client: {e}", exc_info=True)
                self.twilio_client = None
        else:
            logger.warning(
                "Twilio credentials not fully configured. SMS notifications will be disabled.")

        if not self.ntfy_topic:
            logger.warning(
                "NTFY_TOPIC not configured. Ntfy notifications will be disabled.")

        logger.info(
            f"Notification Service Initialized (Enabled: {self.notifications_enabled})")
        if self.twilio_client:
            logger.info(
                f"SMS configured for recipients: {self.sms_recipients}")
        if self.ntfy_topic:
            logger.info(f"Ntfy configured for topic: {self.ntfy_topic}")

    def send_notification(self, notification: Notification):
        """Sends a notification based on its severity and configured channels."""
        if not self.notifications_enabled:
            logger.debug(f"Skipping notification (disabled): {notification}")
            return False  # Indicate not sent

        logger.info(
            f"Attempting to send notification: {notification.event_type.value} ({notification.severity.name}) - ID: {notification.id}")

        sent_sms = False
        sent_ntfy = False

        # --- Define Sending Logic based on Severity ---
        # Example: CRITICAL -> SMS + Ntfy, WARNING -> Ntfy, INFO -> Log only

        if notification.severity == SeverityLevel.CRITICAL:
            # turn of sms for now to prevent using up all our credits
            # sent_sms = self._send_sms(notification)
            sent_sms = True
            sent_ntfy = self._send_ntfy(notification)
        elif notification.severity == SeverityLevel.WARNING:
            sent_ntfy = self._send_ntfy(notification)
        elif notification.severity == SeverityLevel.INFO:
            # For INFO, maybe only log or send to ntfy (TBD)
            # sent_ntfy = self._send_ntfy(notification)
            logger.info(
                f"INFO Notification (not actively sent via SMS/Ntfy by default): {notification.message}")
            pass  # Decide if INFO level should trigger sends

        # Return True if sent successfully via at least one channel requiring active sending
        # Adjust logic based on whether INFO counts as 'sent'
        was_sent = (notification.severity == SeverityLevel.CRITICAL and (sent_sms or sent_ntfy)) or \
                   (notification.severity == SeverityLevel.WARNING and sent_ntfy)
        # Add condition for INFO if it actively sends

        if not was_sent and notification.severity != SeverityLevel.INFO:
            logger.warning(
                f"Notification ID {notification.id} ({notification.severity.name}) was not sent via any active channel.")

        return was_sent  # Or return more detailed status

    def _format_message(self, notification: Notification) -> str:
        """Creates a formatted message string."""
        # Basic formatter, can be expanded
        prefix = f"[{notification.severity.name.upper()}]"
        msg = f"{prefix} {notification.event_type.value}: {notification.message or 'No details.'}"
        if notification.session_id:
            msg += f" (Session: {notification.session_id})"
        if notification.user_id:
            msg += f" (User: {notification.user_id})"
        return msg

    def _send_sms(self, notification: Notification) -> bool:
        """Sends an SMS notification using Twilio."""
        if not self.twilio_client:
            logger.warning(
                f"SMS not sent for {notification.id}: Twilio client not available.")
            return False
        if not self.sms_recipients:
            logger.warning(
                f"SMS not sent for {notification.id}: No recipients configured.")
            return False

        message_body = self._format_message(notification)
        success = True  # Assume success initially
        for phone_number in self.sms_recipients:
            try:
                message = self.twilio_client.messages.create(
                    body=message_body,
                    from_=self.twilio_from_number,
                    to=phone_number
                )
                logger.info(
                    f"SMS sent successfully to {phone_number} (SID: {message.sid})")
            except TwilioRestException as e:
                logger.error(f"Error sending SMS to {phone_number}: {e}")
                success = False
            except Exception as e:
                logger.error(
                    f"Unexpected error sending SMS to {phone_number}: {e}", exc_info=True)
                success = False
        return success

    def _send_ntfy(self, notification: Notification) -> bool:
        """Sends a notification using ntfy."""
        if not self.ntfy_topic:
            logger.warning(
                f"Ntfy notification not sent for {notification.id}: NTFY_TOPIC not configured.")
            return False

        message_body = self._format_message(notification)
        title = f"CSES Alert: {notification.event_type.value}"
        priority_map = {
            SeverityLevel.CRITICAL: 5,  # Max priority
            SeverityLevel.WARNING: 4,  # High priority
            SeverityLevel.INFO: 3     # Default priority
        }

        # --- Add Review URL if present --- >
        review_url = notification.additional_data.get('review_url')
        if review_url:
            message_body += f"\n\n[Review Details]({review_url})"
        # ------------------------------- >

        try:
            headers = {
                'Title': title,
                'Priority': str(priority_map.get(notification.severity, 3)),
                'Tags': f"{notification.severity.name.lower()},{notification.event_type.name.lower()}",
                # --- Add Markdown header --- >
                'markdown': 'true'
                # ------------------------- >
            }
            response = requests.post(
                self.ntfy_topic,
                data=message_body.encode('utf-8'),  # Send raw bytes
                headers=headers
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            logger.info(
                f"Ntfy notification sent successfully to {self.ntfy_topic}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error sending ntfy notification to {self.ntfy_topic}: {e}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending ntfy notification: {e}", exc_info=True)
            return False
