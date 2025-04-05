import paho.mqtt.client as mqtt

# Callback when connecting
def on_connect(client, userdata, flags, rc):
    print(f'Connected with result code {rc}')
    # Subscribe to all topics in the campus/security hierarchy
    client.subscribe('campus/security/#')

# Callback when a message is received
def on_message(client, userdata, msg):
    print(f'Received message on topic {msg.topic}')
    if len(msg.payload) > 100:
        print(f'Message payload too large to display ({len(msg.payload)} bytes)')
    else:
        print(f'Message payload: {msg.payload.decode()}')

# Create MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Connect to broker
client.connect('localhost', 1883, 60)

# Process messages in a loop
print('MQTT Subscriber started. Press Ctrl+C to quit.')
client.loop_forever()
