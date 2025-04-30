import paho.mqtt.client as paho
from paho import mqtt


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"CONNACK received with code {rc}")
    if rc == 0:
        print("Connected successfully!")
        client.publish("campus/security/python_test",
                       payload="Hello from Python", qos=1)
    else:
        print(f"Connection failed, return code: {rc}")


def on_publish(client, userdata, mid, properties=None):
    print(f"mid: {mid} published.")
    client.disconnect()  # Disconnect after publishing


def on_log(client, userdata, level, buf):
    print(f"log: {buf}")


client = paho.Client(client_id="pythonClientTest",
                     userdata=None, protocol=paho.MQTTv5)

# --- Authentication ---
# IMPORTANT: Replace with the actual username and password you set using 'fly secrets set'
# Replace with your actual username secret
MQTT_USERNAME = "kaleb"
# Replace with your actual password secret
MQTT_PASSWORD = "password"
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
# ---------------------

client.on_connect = on_connect
client.on_publish = on_publish
# Uncomment to enable debug logs
client.on_log = on_log
client.enable_logger()

print("Connecting to broker...")
try:
    # Use V3.1.1 which is sometimes more compatible with older setups or proxies
    client.connect("campus-security-evacuation-system.fly.dev", 1883)
    client.loop_forever()
except Exception as e:
    print(f"Connection exception: {e}")
