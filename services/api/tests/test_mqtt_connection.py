# api/tests/test_mqtt_connection.py

import os
import sys
import time
import logging
import json
from datetime import datetime
# dotenv
from dotenv import load_dotenv


# --- Adjust path to import from parent directory ---
# This assumes the script is run from the root of the 'Senior Capstone' directory
# or that the necessary paths are in PYTHONPATH.
script_dir = os.path.dirname(os.path.abspath(__file__))
# Goes up TWO levels from 'tests' to 'services' (assuming tests is under api)
api_root = os.path.dirname(script_dir)
# Goes up THREE levels from 'tests' to project root
project_root = os.path.dirname(api_root)
sys.path.insert(0, project_root)  # Add project root first for `src.` imports


load_dotenv()

try:
    # Use absolute imports from src
    from src.core.config import Config
    from src.services.mqtt_service import MQTTService, TOPIC_UNLOCK_COMMAND
    # Dummy classes for dependencies

    class DummyDB:
        pass

    class DummyFaceClient:
        pass

    class DummyNotificationService:
        pass

    class DummyApp:
        pass  # Add any attributes MQTTService might access if needed
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you run this script from the project root directory")
    print(
        f"or that the '{project_root}' and '{os.path.dirname(project_root)}' directories are in your PYTHONPATH.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)


# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MQTT_TEST")

# --- Environment Variable Check ---
# Include USERNAME and PASSWORD now
required_env_vars = [
    'MQTT_BROKER_ADDRESS',
    'MQTT_BROKER_PORT',
    'SECRET_KEY',
    'MQTT_USERNAME',
    'MQTT_PASSWORD'
]
# Check if var exists and is not empty
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

if missing_vars:
    logger.error(
        f"Missing or empty required environment variables: {', '.join(missing_vars)}")
    logger.error("Please set these variables before running the script.")
    logger.error("Example (PowerShell):")
    logger.error('  $env:MQTT_BROKER_ADDRESS="your_emqx_hostname"')
    logger.error('  $env:MQTT_BROKER_PORT="8883"')
    logger.error('  $env:SECRET_KEY="a_strong_secret_key"')
    logger.error('  $env:MQTT_USERNAME="your_mqtt_username"')
    logger.error('  $env:MQTT_PASSWORD="your_mqtt_password"')
    sys.exit(1)

# --- Instantiate Service ---
logger.info("Creating dummy dependencies and MQTTService instance...")
dummy_app = DummyApp()
dummy_db = DummyDB()
dummy_face_client = DummyFaceClient()
dummy_notification_service = DummyNotificationService()

try:
    mqtt_service = MQTTService(
        app=dummy_app,
        database_service=dummy_db,
        face_client=dummy_face_client,
        notification_service=dummy_notification_service
    )
    logger.info("MQTTService instantiated.")
except Exception as e:
    logger.error(f"Error instantiating MQTTService: {e}", exc_info=True)
    sys.exit(1)


# --- Connect and Test ---
try:
    logger.info("Attempting to connect to MQTT broker...")
    mqtt_service.connect()

    # Wait for connection to establish (adjust time if needed)
    connection_wait_time = 10  # Increased wait time
    logger.info(f"Waiting {connection_wait_time} seconds for connection...")
    time.sleep(connection_wait_time)

    if mqtt_service.client.is_connected():
        logger.info("Successfully connected to MQTT broker via TLS!")

        # --- Publish Test Message ---
        test_payload = {
            "command": "UNLOCK",
            "session_id": "mqtt_test_script",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Test message from Python script"
        }
        payload_str = json.dumps(test_payload)
        topic = TOPIC_UNLOCK_COMMAND  # Use the imported topic constant

        logger.info(f"Publishing test message to topic '{topic}'...")
        logger.debug(f"Payload: {payload_str}")

        result, mid = mqtt_service.client.publish(
            topic, payload=payload_str, qos=1)

        if result == 0:  # paho.mqtt.client.MQTT_ERR_SUCCESS
            logger.info(f"Message published successfully (MID: {mid}).")
        else:
            logger.error(f"Failed to publish message (Error code: {result}).")

        # Wait a moment before disconnecting
        time.sleep(2)

    else:
        logger.error("Failed to connect to MQTT broker after waiting.")
        logger.error(
            "Check broker address, port, CA certificate path, and network connectivity.")
        # Additional debug: Check MQTT client state
        try:
            # Access internal state for debug
            logger.error(f"MQTT Client State: {mqtt_service.client._state}")
            # Access internal state for debug
            logger.error(
                f"MQTT Client Last Error: {mqtt_service.client._last_error}")
        except AttributeError:
            logger.error(
                "Could not retrieve MQTT client internal state details.")


except Exception as e:
    logger.error(f"An error occurred during the test: {e}", exc_info=True)

finally:
    # --- Disconnect ---
    if mqtt_service and mqtt_service.client.is_connected():
        logger.info("Disconnecting MQTT client...")
        mqtt_service.disconnect()
        logger.info("MQTT client disconnected.")
    elif mqtt_service:
        logger.info("MQTT client was not connected, stopping loop if running.")
        # Ensure loop stops even if disconnect fails/wasn't needed
        mqtt_service.client.loop_stop()
    else:
        logger.info("MQTT service not initialized, skipping disconnect.")

logger.info("Test script finished.")
