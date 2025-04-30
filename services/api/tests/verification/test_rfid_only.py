#!/usr/bin/env python3
import os
import ssl
import json
import base64
import uuid
import io
from datetime import datetime, timezone
from PIL import Image, ImageOps
import paho.mqtt.client as mqtt

# --- Configuration ---
# Use an employee's image who has an RFID tag in sample_data.sql
# Example: Griffin Holvert (EMP022)
EMPLOYEE_ID_FOR_TEST = "EMP022"
# Use raw string for path
IMAGE_PATH = rf"..\..\static\images\tests\rfid_only_review.png"
MQTT_BROKER = "z8002768.ala.us-east-1.emqxsl.com"
MQTT_PORT = 8883
MQTT_USERNAME = "kalebcole"
MQTT_PASSWORD = "cses"
CA_CERT_PATH = r"..\..\certs\emqxsl-ca.crt"  # Use raw string for path
MQTT_TOPIC = "campus/security/session"
DEVICE_ID = f"python-pub-test-rfid-only"

# --- Image Processing ---
try:
    orig = Image.open(IMAGE_PATH)
    print("Applying EXIF orientation if present...")
    orig = ImageOps.exif_transpose(orig)

    # Resize so max dimension is 320px
    # Consider Image.Resampling.LANCZOS for newer Pillow
    orig.thumbnail((320, 320), Image.Resampling.LANCZOS)

    # Ensure image is in RGB mode before saving as JPEG
    if orig.mode == 'RGBA':
        print("Converting image from RGBA to RGB...")
        orig = orig.convert('RGB')

    buf = io.BytesIO()
    # Re-encode JPEG at reduced quality
    orig.save(buf, format="JPEG", quality=50)
    image_bytes = buf.getvalue()
    buf.close()

    b64_image = base64.b64encode(image_bytes).decode("ascii")
    image_size = len(image_bytes)
    print(f"Reduced image '{IMAGE_PATH}' to {image_size} bytes")

except FileNotFoundError:
    print(f"Error: Image file not found at {IMAGE_PATH}")
    exit(1)
except Exception as e:
    print(f"Error processing image: {e}")
    exit(1)

# --- Payload Construction (RFID Only Scenario) ---
payload = {
    "device_id": DEVICE_ID,
    "session_id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "session_duration": 1500,  # Example duration
    "image_size": image_size,
    "image": b64_image,
    "rfid_tag": EMPLOYEE_ID_FOR_TEST,  # Include the RFID tag
    "rfid_detected": True,           # Indicate RFID was detected
    "face_detected": False,          # Indicate FACE was NOT detected
}

payload_str = json.dumps(payload, separators=(",", ":"))
print(f"Total payload size: {len(payload_str)} bytes")
print(
    f"Scenario: RFID Only (Employee: {EMPLOYEE_ID_FOR_TEST}, Face Detected: False)")

# --- MQTT Connection & Publish ---
client = mqtt.Client(client_id=DEVICE_ID, protocol=mqtt.MQTTv311)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
try:
    client.tls_set(ca_certs=CA_CERT_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(False)

    print(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()  # Start network loop

    print(f"Publishing to {MQTT_TOPIC}...")
    res = client.publish(MQTT_TOPIC, payload_str, qos=0, retain=False)
    res.wait_for_publish(timeout=5)  # Wait for publish confirmation

    if res.rc == mqtt.MQTT_ERR_SUCCESS:
        print("✅ Success")
    else:
        print(f"❌ Fail ({res.rc}): {mqtt.error_string(res.rc)}")

except FileNotFoundError:
    print(f"Error: CA certificate file not found at {CA_CERT_PATH}")
except ConnectionRefusedError:
    print(
        f"Error: Connection refused by broker {MQTT_BROKER}:{MQTT_PORT}. Check broker status, credentials, and TLS settings.")
except mqtt.WebsocketConnectionError as e:
    print(f"WebSocket Error: {e}")
except Exception as e:
    print(f"MQTT Error: {e}")
finally:
    client.loop_stop()
    client.disconnect()
    print("Disconnected.")
