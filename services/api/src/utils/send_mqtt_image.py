#!/usr/bin/env python3
import os
import ssl
import json
import base64
import uuid
import io                              # ← add this
from datetime import datetime, timezone
from PIL import Image                 # ← and this
import paho.mqtt.client as mqtt

# ─── Configuration ─────────────────────────────────────────────────────────────
IMAGE_PATH = r"C:\Users\kaleb\Documents\00_College\Senior Capstone\services\api\static\images\tests\Griffin.jpg"
MQTT_BROKER = "z8002768.ala.us-east-1.emqxsl.com"
MQTT_PORT = 8883
MQTT_USERNAME = "kalebcole"
MQTT_PASSWORD = "cses"
CA_CERT_PATH = r"..\..\certs\emqxsl-ca.crt"
MQTT_TOPIC = "campus/security/session"
DEVICE_ID = "python-pub-01"
# ────────────────────────────────────────────────────────────────────────────────

# 1) Open, downsample, recompress
orig = Image.open(IMAGE_PATH)
# Resize so max dimension is 768
orig.thumbnail((768, 768), Image.LANCZOS)

buf = io.BytesIO()
# Re-encode JPEG at 50% quality
orig.save(buf, format="JPEG", quality=50)
small_jpeg = buf.getvalue()
buf.close()

# 2) Base64-encode the smaller JPEG
b64_image = base64.b64encode(small_jpeg).decode("ascii")
image_size = len(small_jpeg)
print(f"Reduced image to {image_size} bytes (≈{len(b64_image)} base64 chars)")

# 3) Build payload
payload = {
    "device_id": DEVICE_ID,
    "session_id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc)
    .isoformat()
    .replace("+00:00", "Z"),
    "session_duration": 1500,
    "image_size": image_size,
    "image": b64_image,
    "rfid_tag": "EMP022",
    "rfid_detected": True,
    "face_detected": True,
}

payload_str = json.dumps(payload, separators=(",", ":"))
print(f"Total payload size: {len(payload_str)} bytes")

# 4) MQTT setup & publish
client = mqtt.Client(client_id=DEVICE_ID, protocol=mqtt.MQTTv311)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.tls_set(ca_certs=CA_CERT_PATH,
               tls_version=ssl.PROTOCOL_TLSv1_2)
client.tls_insecure_set(False)

print(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}…")
client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)

print(f"Publishing to {MQTT_TOPIC}…")
res = client.publish(MQTT_TOPIC, payload_str, qos=1, retain=False)
res.wait_for_publish()

print("✅ Success" if res.rc == mqtt.MQTT_ERR_SUCCESS else f"❌ Fail ({res.rc})")
client.disconnect()
