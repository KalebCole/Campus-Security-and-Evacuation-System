import paho.mqtt.client as mqtt
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RFIDHandler:
    def __init__(self, broker_address: str = "localhost", broker_port: int = 1883):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Connect to broker
        logger.info(
            f"Connecting to MQTT broker at {broker_address}:{broker_port}")
        self.client.connect(broker_address, broker_port, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to RFID topic
            client.subscribe("campus/security/rfid/#")
            logger.info("Subscribed to RFID topics")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received RFID message: {payload}")

            # Process the RFID scan
            rfid_tag = payload.get("rfid_tag")
            device_id = payload.get("device_id")

            if rfid_tag and device_id:
                logger.info(f"RFID scan from device {device_id}: {rfid_tag}")
                # Here you would typically:
                # 1. Verify the RFID tag
                # 2. Create a session
                # 3. Send a response back to the Arduino

                # Example response
                response = {
                    "status": "success",
                    "message": f"RFID {rfid_tag} processed",
                    "device_id": device_id
                }

                # Publish response
                self.publish_response(device_id, response)

        except json.JSONDecodeError:
            logger.error("Invalid JSON payload received")
        except Exception as e:
            logger.error(f"Error processing RFID message: {str(e)}")

    def publish_response(self, device_id: str, response: Dict[str, Any]):
        """Publish a response back to the Arduino"""
        topic = f"campus/security/rfid/response/{device_id}"
        try:
            self.client.publish(topic, json.dumps(response))
            logger.info(f"Published response to {topic}: {response}")
        except Exception as e:
            logger.error(f"Error publishing response: {str(e)}")

    def cleanup(self):
        """Clean up resources"""
        self.client.loop_stop()
        self.client.disconnect()
