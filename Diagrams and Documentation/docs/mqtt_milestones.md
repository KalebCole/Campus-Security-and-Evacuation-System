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

## II. Required Updates (Gaps to Target)

1.  **MQTT Broker:**
    *   Implement authentication (remove anonymous access).
    *   Configure and enable TLS/SSL for secure connections.
2.  **Server:**
    *   **Major Session Logic Overhaul:**
        *   Change `session_handler.py` (or replace/refactor) to *publish* unified session state updates to the single `campus/security/session` topic.
        *   Implement logic to create/update sessions upon receiving *either* `/face` or `/rfid` data.
        *   Implement tracking of partial (`rfid_verified`, `face_verified`) and complete (`auth_status`) authentication within the session state.
        *   Remove old `/response` topic publishing.
    *   **New Channel Handling:**
        *   Implement subscription and processing for `campus/security/face`.
        *   Implement subscription and processing for `campus/security/activate`.
        *   Implement subscription *and* publishing logic for `campus/security/emergency/+`.
    *   **Core Logic:**
        *   Integrate GhostFaceNet for embedding generation from `/face` data.
        *   Integrate full database querying (Supabase/pgvector) for RFID validation and face matching.
        *   Implement logic to coordinate RFID and Face verification results for final session status.
3.  **Arduino Uno R4 Client:**
    *   **Replace HTTP with MQTT:** Implement a robust MQTT client (e.g., using PubSubClient library).
    *   **Implement Publishing:**
        *   Publish to `campus/security/rfid` upon tag scan.
        *   Publish to `campus/security/activate` upon motion detection trigger.
        *   Publish to `campus/security/emergency/+` upon emergency pull station trigger.
    *   **Implement Subscribing:**
        *   Subscribe to `campus/security/session` to receive session updates.
        *   Subscribe to `campus/security/emergency/+` to receive emergency alerts.
    *   **Implement Logic:**
        *   Act on received `/session` messages (e.g., control door servo).
        *   Act on received `/emergency/+` messages (e.g., unlock door, activate lights).
    *   **Hardware Integration:** Connect and configure RCWL-0516 sensor and MS-7 pull station interrupts.
4.  **ESP32-CAM Client:**
    *   **Implement Application:** Create C++/ESP-IDF application using ESP-WHO for face detection/cropping.
    *   **Implement MQTT Client:** Add MQTT client library and connection logic.
    *   **Implement Publishing:** Publish to `campus/security/face` with image data when triggered.
    *   **Implement Subscribing:**
        *   Subscribe to `campus/security/activate` to trigger image capture.
        *   Subscribe to `campus/security/session` to potentially update local state (if needed).
        *   Subscribe to `campus/security/emergency/+`.
    *   **Implement Logic:** Act on received `/activate` and `/emergency/+` messages.
5.  **General:**
    *   Ensure standardized JSON payload formats (as defined in `mqtt.md`) are used by all components.
    *   Implement robust error handling (connection loss, timeouts, invalid messages) and reconnection logic on all clients.

## III. Milestones and Tasks

### Milestone 1: Foundational Server Core Refactor
*   **Task 1.1 (Server):** Refactor `session_handler.py` (or create a new handler `mqtt_handler.py`) to implement the *new* session management logic:
    *   Subscribes to `/face` and `/rfid`.
    *   Creates/updates a unified session state (in memory).
    *   Tracks `rfid_verified` / `face_verified` / `auth_status`.
    *   Publishes session updates to the single `campus/security/session` topic.
*   **Task 1.2 (Server):** Implement subscription handlers (stubs for now, just log messages) for `/activate` and `/emergency/+` within the new handler.
*   **Task 1.3 (Server):** Define and document the standard JSON payload schemas for all channels (as per `mqtt.md`).
*   **Task 1.4 (Server):** Implement basic database interaction layer (`database_interface.py`) for storing/retrieving user data and session state (stubs only).

### Milestone 2: Arduino Integration (MQTT, Activation, RFID)
*   **Task 2.1 (Arduino):** Implement MQTT client connection (to port 1883) and basic publish/subscribe capability.
*   **Task 2.2 (Arduino):** Integrate motion sensor (RCWL-0516) and implement publishing to `campus/security/activate` on trigger.
*   **Task 2.3 (Arduino):** Implement publishing RFID tag data to `campus/security/rfid` using the standard payload.
*   **Task 2.4 (Arduino):** Implement subscription to `campus/security/session` (log received messages for now).
*   **Task 2.5 (Arduino):** Implement subscription to `campus/security/emergency/+` (log received messages).
*   **Task 2.6 (Server):** Fully implement the processing logic for incoming `/activate` messages (e.g., update system state).
*   **Task 2.7 (Server):** Fully implement the processing logic for incoming `/rfid` messages (validate tag, update session state, publish session update).
*   **Task 2.8 (Testing):** Test the Arduino -> Server flow for Activation and RFID channels, including session updates published by the server.

### Milestone 3: ESP32-CAM Integration (MQTT, Face Processing)
*   **Task 3.1 (ESP32):** Implement ESP-WHO based application for face detection/cropping.
*   **Task 3.2 (ESP32):** Implement MQTT client connection (to port 1883).
*   **Task 3.3 (ESP32):** Implement subscription to `campus/security/activate`. Trigger image capture/processing upon receiving activation message.
*   **Task 3.4 (ESP32):** Implement publishing cropped face image data to `campus/security/face` using the standard payload.
*   **Task 3.5 (ESP32):** Implement subscription to `campus/security/session` (log messages).
*   **Task 3.6 (ESP32):** Implement subscription to `campus/security/emergency/+` (log messages).
*   **Task 3.7 (Server):** Implement GhostFaceNet model loading and embedding generation logic.
*   **Task 3.8 (Server):** Fully implement the processing logic for incoming `/face` messages (generate embedding, query DB for match, update session state, publish session update).
*   **Task 3.9 (Testing):** Test the ESP32 -> Server flow for the Face channel. Test the server's ability to update sessions based on face data.

### Milestone 4: End-to-End Logic & Emergency Handling
*   **Task 4.1 (Server):** Finalize server logic to correctly transition session `auth_status` to "complete" only when *both* RFID and Face are verified within a session timeout period. Ensure correct final session message is published.
*   **Task 4.2 (Arduino):** Implement logic to react to `campus/security/session` messages (e.g., control door servo based on `access_granted` field).
*   **Task 4.3 (Arduino):** Integrate emergency pull station (MS-7) and implement publishing to `campus/security/emergency/+` on trigger.
*   **Task 4.4 (Arduino):** Implement logic to react to `campus/security/emergency/+` messages (e.g., unlock door, activate strobe light).
*   **Task 4.5 (Server):** Implement server-side logic for handling `/emergency/+` messages (log, notify personnel, potentially publish broadcast).
*   **Task 4.6 (ESP32):** Implement any required logic to react to `/session` or `/emergency/+` messages.
*   **Task 4.7 (Testing):** Conduct end-to-end tests for the full successful authentication flow (Activation -> RFID -> Face -> Session Complete -> Door Unlock). Test failure scenarios (timeout, mismatch). Test the emergency flow.

### Milestone 5: Hardening, Testing & Documentation Finalization
*   **Task 5.1 (All):** Implement comprehensive error handling and reconnection logic on Arduino, ESP32, and Server MQTT clients.
*   **Task 5.2 (Testing):** Develop and run integration tests covering various scenarios.
*   **Task 5.3 (Security):** *[Deferred]* Review and harden security configurations (broker ACLs, credential management).
*   **Task 5.4 (Docs):** Update all relevant documentation (`README.md` files, `mqtt.md`, setup guides) to reflect the final implementation.
