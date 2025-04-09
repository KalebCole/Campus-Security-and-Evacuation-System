# MQTT Architecture Documentation

## Overview
This document outlines the MQTT-based communication architecture for the Campus Security and Evacuation System (CSES). The system uses MQTT for real-time communication between hardware components (ESP32-CAM, Arduino Uno R4) and the Flask server.

## System Components

### Hardware Components
1. **ESP32-CAM**
   - Handles face detection and image capture
   - Uses ESP-WHO framework for face detection
   - Publishes face data to MQTT broker

2. **Arduino Uno R4**
   - Handles RFID reading
   - Controls door locks via servo motors
   - Manages emergency protocols
   - Detects motion via RCWL-0516 sensors

3. **Flask Server**
   - Processes authentication workflows
   - Manages sessions
   - Handles database operations
   - Coordinates emergency responses

## MQTT Channels

### Face Detection Channel
- **Topic**: `campus/security/face`
- **Publisher**: ESP32-CAM
- **Subscriber**: Flask Server
- **Payload Format**:
  ```json
  {
    "device_id": "esp32-cam-01",
    "image": "base64_encoded_image",
    "timestamp": "2025-04-09T09:46:00Z"
  }
  ```
- **Responsibilities**:
  - ESP32-CAM: Captures and processes images, publishes face data
  - Server: Processes face data, generates embeddings, performs verification

### RFID Channel
- **Topic**: `campus/security/rfid`
- **Publisher**: Arduino Uno R4
- **Subscriber**: Flask Server
- **Payload Format**:
  ```json
  {
    "rfid_tag": "A1B2C3D4",
    "device_id": "arduino-door-01",
    "timestamp": "2025-04-09T09:46:00Z"
  }
  ```
- **Responsibilities**:
  - Arduino: Reads and publishes RFID data
  - Server: Validates RFID tags, logs access attempts

### Session Channel
- **Topic**: `campus/security/session`
- **Publisher**: Flask Server
- **Subscribers**: ESP32-CAM, Arduino Uno R4
- **Payload Format**:
  ```json
  {
    "session_id": "ABC123",
    "status": "active",
    "device_id": "arduino-door-01",
    "timestamp": "2025-04-09T09:46:00Z"
  }
  ```
- **Responsibilities**:
  - Server: Creates and manages sessions
  - Hardware: Updates state based on session status

### Activation Channel
- **Topic**: `campus/security/activate`
- **Publisher**: Arduino Uno R4
- **Subscribers**: Flask Server, ESP32-CAM
- **Payload Format**:
  ```json
  {
    "device_id": "arduino-door-01",
    "active": true,
    "timestamp": "2025-04-09T09:46:00Z"
  }
  ```
- **Responsibilities**:
  - Arduino: Detects motion, activates system
  - Server: Updates system state
  - ESP32-CAM: Begins face detection

### Emergency Stop Channel
- **Topic**: `campus/security/emergency/+`
- **Publisher**: Arduino Uno R4, Flask Server
- **Subscribers**: All components
- **Payload Format**:
  ```json
  {
    "emergency": true,
    "source": "pull_station",
    "timestamp": "2025-04-09T09:46:00Z"
  }
  ```
- **Responsibilities**:
  - Arduino: Detects emergencies, unlocks doors
  - Server: Logs events, sends notifications
  - ESP32-CAM: Responds to emergency state

## Message Flow

1. **System Activation**
   - Motion detected by Arduino
   - Arduino publishes to `campus/security/activate`
   - System components receive activation

2. **Authentication Process**

   a. **Initial Session Creation**
      - When either RFID or face data is received, server creates a session
      - Server publishes session ID to `campus/security/session`
      - Session includes partial authentication status
      - Example session payload:
        ```json
        {
          "session_id": "ABC123",
          "device_id": "arduino-door-01",
          "auth_status": "partial",
          "rfid_verified": false,
          "face_verified": false,
          "timestamp": "2025-04-09T09:46:00Z"
        }
        ```

   b. **RFID Authentication**
      - Arduino reads RFID, publishes to `campus/security/rfid`
      - Server creates/updates session with RFID data
      - Server queries database for RFID match
      - Updates session with RFID verification status
      - Publishes updated session to `campus/security/session`

   c. **Face Authentication**
      - ESP32-CAM captures face, publishes to `campus/security/face`
      - Server creates/updates session with face data
      - Server processes face data, generates embedding
      - Queries database for face match
      - Updates session with face verification status
      - Publishes updated session to `campus/security/session`

   d. **Complete Authentication**
      - Server monitors session for both RFID and face verification
      - When both are verified, updates session status to "complete"
      - Publishes final session status to `campus/security/session`
      - Example complete session payload:
        ```json
        {
          "session_id": "ABC123",
          "device_id": "arduino-door-01",
          "auth_status": "complete",
          "rfid_verified": true,
          "face_verified": true,
          "user_id": "user123",
          "access_granted": true,
          "timestamp": "2025-04-09T09:46:00Z"
        }
        ```

3. **Emergency Response**
   - Emergency detected
   - Emergency message published to `campus/security/emergency/+`
   - All components respond accordingly

## Security Considerations

1. **Access Control**
   - Topic-level access control *[Note: Requires broker configuration - deferred]*
   - Device-specific permissions *[Note: Requires broker configuration - deferred]*
   - Emergency override capabilities

## Testing

1. **Component Testing**
   - Test each channel independently
   - Verify message formats
   - Check error handling

2. **Integration Testing**
   - Test complete authentication flow
   - Verify emergency response
   - Check system recovery

3. **Performance Testing**
   - Measure message latency
   - Test under load
   - Verify reliability

## Implementation Notes

1. **Error Handling**
   - Connection recovery
   - Message retry logic
   - State synchronization

2. **Monitoring**
   - Message logging
   - System status tracking
   - Performance metrics