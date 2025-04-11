# MQTT Setup Documentation

## Overview
This directory contains the MQTT broker (Mosquitto) configuration and related components for the Campus Security System. The MQTT broker acts as a message broker between the Arduino clients and the server.

## Directory Structure
```
mqtt/
├── config/           # Mosquitto configuration files
│   └── mosquitto.conf
├── data/            # Persistent data storage
├── log/             # Log files
```

## Mosquitto Configuration
The `mosquitto.conf` file contains the following key settings:
```conf
listener 1883              # Listen on port 1883
allow_anonymous true       # Allow connections without authentication
persistence true           # Enable message persistence
persistence_location /mosquitto/data/  # Where to store persistent data
log_dest file /mosquitto/log/mosquitto.log  # Log file location
log_dest stdout           # Also log to console
```

## Docker Setup
The Mosquitto broker runs in a Docker container. To run it:

1. Build and start the container:
```powershell
docker-compose up -d
```

2. Check if the container is running:
```powershell
docker ps | findstr mosquitto
```

3. View logs:
```powershell
docker logs mosquitto
```

## Network Configuration
- The MQTT broker listens on port 1883
- By default, it's accessible from:
  - The host machine (localhost)
  - Other containers in the same Docker network
- To make it accessible from other devices on your network:
  - Use your computer's IP address instead of localhost
  - Ensure port 1883 is properly exposed in Docker

## Testing the Connection
1. Start the Python subscriber:
```powershell
python mqtt_subscriber.py
```

2. Test publishing a message:
```powershell
python -c "import paho.mqtt.client as mqtt; client = mqtt.Client(); client.connect('localhost', 1883); client.publish('campus/security/status', '{\"device_id\":\"test\",\"status\":\"online\"}')"
```

## Troubleshooting
1. **Can't connect from Arduino**
   - Check if the broker is running: `docker ps | findstr mosquitto`
   - Verify port 1883 is exposed: `netstat -an | findstr 1883`
   - Try using your computer's IP address instead of localhost
   - Check Windows Firewall settings

2. **Connection Refused**
   - Ensure Mosquitto is running
   - Check if port 1883 is already in use
   - Verify Docker network configuration

3. **Authentication Issues**
   - Current setup allows anonymous connections
   - If authentication is needed, update mosquitto.conf

## Security Considerations
- Current setup allows anonymous connections (for development)
- For production:
  - Enable authentication
  - Use TLS/SSL
  - Restrict access to specific IPs
  - Use strong passwords 