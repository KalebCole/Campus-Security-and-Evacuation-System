# MQTT Implementation Milestones and Tasks

This document outlines the current state of the system regarding MQTT, the required updates to meet the architecture defined in `mqtt.md`, and the milestones to achieve this.

## I. Current System State (MQTT Aspects)

1.  **MQTT Broker:**
    *   Mosquitto broker setup via Docker (`mqtt/docker-compose.yml`).
    *   Currently configured for anonymous access (`mqtt/README.md`).
    *   Basic persistence and logging are configured.
    *   No TLS/SSL configured.
2.  **Server (`server/mqtt/`):**
    *   Has `session_handler.py` and `rfid_handler.py`.
    *   `session_handler.py`:
        *   Subscribes to `campus/security/session` and `campus/security/status`.
        *   *Expects* requests *from* devices on these topics.
        *   Publishes *responses* to separate `/response` topics (e.g., `campus/security/session/response`).
        *   Manages sessions in memory with basic creation logic based on incoming requests.
    *   `rfid_handler.py`: Likely subscribes to an RFID topic (needs confirmation on exact topic used currently) and processes incoming RFID data.
    *   Overall server logic for combining RFID/Face and managing the *unified* session state described in `mqtt.md` is not implemented.
    *   Face processing uses TensorFlow (planned replacement: GhostFaceNet).
    *   Database integration (Supabase/pgvector) is partial/planned.
3.  **Arduino Uno R4 Client:**
    *   Currently uses HTTP for communication (`PROJECT_STATUS_2025-04-05.md`).
    *   Has a state machine (`Arduino Uno R4 Client/src/main.cpp`) but needs MQTT client implementation.
    *   Motion detection trigger (RCWL-0516) integration is planned/needed for the `/activate` channel.
    *   Emergency pull station (MS-7) integration is planned/needed for the `/emergency/+` channel.
4.  **ESP32-CAM Client:**
    *   Basic implementation exists (`PROJECT_STATUS_2025-04-05.md`), likely not using MQTT or ESP-WHO as targeted.
    *   Needs full C++/ESP-IDF implementation with ESP-WHO and MQTT client.
    *   Needs logic to be triggered by the `/activate` channel.

## II. Required Updates for api

I'll outline an iterative approach to implement the MQTT handlers, focusing on getting basic functionality working first and then building up. Here's the plan:

### Iteration 1: Basic MQTT Connection & Session Management
1. **Setup Basic MQTT Handler**
   - Create simple `mqtt_handler.py` that:
     - Connects to Mosquitto
     - Handles basic connection/reconnection
     - Logs connection status
   - Test with simple publish/subscribe

2. **Basic Session Management**
   - Implement simple `session_handler.py` that:
     - Creates sessions in memory
     - Tracks basic session state
     - Publishes to `campus/security/session`
   - No complex state management yet

### Iteration 2: RFID Integration
1. **RFID Handler**
   - Implement `rfid_handler.py` that:
     - Subscribes to `campus/security/rfid`
     - Validates RFID tags against database
     - Updates session state
   - Test with mock RFID data

2. **Database Integration**
   - Connect RFID validation to existing database
   - Simple queries for RFID matching
   - Basic logging

### Iteration 3: Face Detection Integration
1. **Face Handler**
   - Implement face data reception
   - Connect to existing face recognition service
   - Update session state with face verification
   - Test with mock face data

2. **Session Completion**
   - Implement basic session completion logic
   - Publish final session status
   - Test complete authentication flow

### Iteration 4: System Activation & Emergency
1. **Activation Handler**
   - Implement `campus/security/activate` subscription
   - Basic system state management
   - Test activation flow

2. **Emergency Handler**
   - Implement `campus/security/emergency/+` handling
   - Basic emergency response
   - Test emergency scenarios

### Iteration 5: Error Handling & Recovery
1. **Connection Recovery**
   - Implement reconnection logic
   - Handle connection drops
   - Test recovery scenarios

2. **Error Handling**
   - Add basic error handling
   - Log errors appropriately
   - Test error scenarios

### Iteration 6: Testing & Documentation
1. **Testing**
   - Create test suite for each handler
   - Test integration scenarios
   - Document test results

2. **Documentation**
   - Update documentation
   - Add usage examples
   - Document known limitations

Each iteration builds on the previous one, focusing on getting core functionality working before adding complexity. Would you like me to start with implementing any specific iteration?
