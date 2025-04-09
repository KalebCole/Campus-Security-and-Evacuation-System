# Project Troubleshooting Guide

This guide documents common issues encountered during development and how to resolve them.

## Networking

### MQTT/Server Connection Issues (Local Development)

**Symptom:**

*   Device (ESP32-CAM, Arduino Uno R4) fails to connect to the local MQTT broker or backend server running on the development machine (e.g., in Docker).
*   Errors might include:
    *   MQTT connection failed (rc=-2, rc=-4, or others)
    *   TCP connection failed/timed out
    *   HTTP request failed

**Cause:**

The device and the computer hosting the server/broker **must be connected to the same local network** for direct communication using private IP addresses (like `192.168.x.x` or `172.20.x.x` from a mobile hotspot) to work.

If the device is connected to one WiFi network (e.g., a mobile hotspot) and the computer is connected to a different WiFi network or wired Ethernet that's not part of the first network, the device cannot route traffic to the computer's private IP address on the hotspot network.

**Resolution:**

Ensure both the IoT device (ESP32-CAM, Arduino) and the computer running the server/broker (e.g., Docker host) are connected to the **same WiFi network**. In the common development setup for this project, this means connecting both to the **"iPod Mini" mobile hotspot**.

**Verification:**

*   Check the IP address assigned to the device (usually printed in its serial monitor output).
*   Check the IP address assigned to the computer *on that specific network interface* (e.g., the WiFi adapter connected to the hotspot). You can use `ipconfig` (Windows PowerShell) or `ip addr` (Linux/WSL) for this.
*   Ensure the IP address used in the device's code (`MQTT_BROKER`, server URL) matches the computer's IP address on the shared network.
