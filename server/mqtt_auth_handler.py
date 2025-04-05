import paho.mqtt.client as mqtt
import json
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MQTTAuthHandler:
    def __init__(self, broker_address="localhost", broker_port=1883):
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.client = mqtt.Client()
        self.authenticated_devices = {}  # Store authenticated devices

        # Load device secrets from environment or config
        self.device_secrets = {
            "esp32cam_1": os.getenv("ESP32CAM1_SECRET", "YOUR_DEVICE_SECRET"),
            # Add more devices as needed
        }

        # Set up MQTT client
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(os.getenv("MQTT_USERNAME", ""),
                                    os.getenv("MQTT_PASSWORD", ""))

        # Connect to broker
        self.client.connect(broker_address, broker_port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to authentication topic
            client.subscribe("campus/security/auth")
            client.subscribe("campus/security/status")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic

            if topic == "campus/security/auth":
                self.handle_auth_request(payload)
            elif topic == "campus/security/status":
                self.handle_status_request(payload)

        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def handle_auth_request(self, payload):
        device_id = payload.get("device_id")
        secret = payload.get("secret")

        if not device_id or not secret:
            logger.error(
                "Invalid authentication request: missing device_id or secret")
            return

        # Check if device is known and secret matches
        if device_id in self.device_secrets and self.device_secrets[device_id] == secret:
            # Device is authenticated
            self.authenticated_devices[device_id] = {
                "last_seen": datetime.now(),
                "status": "authenticated"
            }

            # Send authentication response
            response = {
                "device_id": device_id,
                "status": "authenticated",
                "timestamp": datetime.now().isoformat()
            }

            self.client.publish(f"campus/security/auth/{device_id}",
                                json.dumps(response))
            logger.info(f"Device {device_id} authenticated successfully")
        else:
            # Authentication failed
            response = {
                "device_id": device_id,
                "status": "failed",
                "reason": "invalid_credentials",
                "timestamp": datetime.now().isoformat()
            }

            self.client.publish(f"campus/security/auth/{device_id}",
                                json.dumps(response))
            logger.warning(f"Authentication failed for device {device_id}")

    def handle_status_request(self, payload):
        device_id = payload.get("device_id")
        status = payload.get("status")

        if not device_id or not status:
            logger.error("Invalid status request: missing device_id or status")
            return

        if device_id in self.authenticated_devices:
            # Update device status
            self.authenticated_devices[device_id]["last_seen"] = datetime.now()
            self.authenticated_devices[device_id]["status"] = status

            # Send status acknowledgment
            response = {
                "device_id": device_id,
                "status": "acknowledged",
                "timestamp": datetime.now().isoformat()
            }

            self.client.publish(f"campus/security/status/{device_id}",
                                json.dumps(response))
            logger.info(f"Status update received from device {device_id}")

    def check_device_status(self, device_id):
        """Check if a device is authenticated and active"""
        if device_id in self.authenticated_devices:
            device = self.authenticated_devices[device_id]
            # Consider device inactive if not seen for 5 minutes
            if (datetime.now() - device["last_seen"]).total_seconds() > 300:
                return False
            return device["status"] == "authenticated"
        return False

    def emergency_stop(self, device_id=None):
        """Send emergency stop command to all or specific devices"""
        command = {
            "command": "emergency_stop",
            "timestamp": datetime.now().isoformat()
        }

        if device_id:
            # Stop specific device
            self.client.publish(f"campus/security/status/{device_id}",
                                json.dumps(command))
        else:
            # Stop all devices
            self.client.publish("campus/security/status",
                                json.dumps(command))

    def cleanup(self):
        """Clean up resources"""
        self.client.loop_stop()
        self.client.disconnect()
