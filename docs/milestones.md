# Project Milestones - Arduino Mega Central Control Architecture

This document outlines the milestones required to transition the CSES project to the new architecture where the Arduino Mega acts as the central sensor and control hub, communicating directly with the ESP32-CAM via wired signals.

**Current State:**
*   Arduino code exists for Uno R4 (needs porting to Mega).
*   ESP32 code exists (needs modification for wired signals).
*   ESP32 reads motion sensor directly.
*   ESP32 subscribes to `/rfid` MQTT topic.
*   Arduino publishes RFID data to `/rfid` MQTT topic.
*   Project Overview and ESP32 README reflect the old architecture.

**Target State:**
*   Arduino Mega handles all sensor inputs (Motion, RFID, Emergency).
*   Arduino Mega controls servo via connected Arduino Uno.
*   Arduino Mega sends digital signals to ESP32 for Motion and RFID detection events.
*   ESP32 receives signals from Mega via input pins.
*   ESP32 packages session data (including RFID status based on Mega signal) and sends to `/session` MQTT topic.
*   `/rfid` MQTT topic is deprecated.
*   Documentation reflects the new architecture.

---

## Milestone 1: Hardware Setup & Basic Wiring

**Goal:** Physically wire the components according to the new architecture.

*   [X] **Hardware Acquisition:** Ensure Arduino Mega, ESP32-CAM, Motion Sensor, RFID Reader, Emergency Button, Arduino Uno (for Servo), and Servo Motor are available.
*   [ ] **Mega Sensor Wiring:**
    *   [ ] Connect Motion Sensor output to a digital input pin on the Mega.
    *   [ ] Connect RFID Reader output to a digital input pin on the Mega (implement pull-up resistor as needed, expecting LOW on detection).
    *   [ ] Connect Emergency Button output to a digital input pin on the Mega.
*   [ ] **Mega Servo Control Wiring:**
    *   [ ] Connect a digital output pin on the Mega to a digital input pin on the Arduino Uno (Servo Controller).
    *   [ ] Wire the Arduino Uno to the Servo Motor.
*   [ ] **Mega <-> ESP32 Wiring:**
    *   [ ] Connect a digital output pin on the Mega (Motion Signal Out) to a digital input pin on the ESP32 (Motion Signal In).
    *   [ ] Connect a digital output pin on the Mega (RFID Signal Out) to a digital input pin on the ESP32 (RFID Signal In).
    *   [ ] Ensure a common ground connection between the Mega and ESP32.
*   [ ] **Power:** Ensure all components (Mega, ESP32, Uno, Sensors, Servo) are appropriately powered.

## Milestone 2: Arduino Mega Firmware Development

**Goal:** Implement the core logic on the Arduino Mega to read sensors and send signals.

*   [X] **Project Setup:** Create/Update PlatformIO project for Arduino Mega.
*   [X] **Pin Definitions:** Define input pins for Motion, RFID, Emergency sensors.
*   [X] **Output Pin Definitions:** Define output pins for Motion Signal (to ESP32), RFID Signal (to ESP32), and Servo Trigger (to Uno).
*   [/] **Sensor Reading:**
    *   [/] Implement logic to read the Motion Sensor state (debouncing if necessary).
    *   [/] Implement logic to read the RFID Sensor state (detecting the LOW signal).
    *   [/] Implement logic to read the Emergency Button state.
*   [/] **Signal Generation:**
    *   [/] When motion is detected, send a defined signal (e.g., pulse HIGH) on the Motion Signal output pin.
    *   [/] When RFID is detected (LOW state), send a defined signal on the RFID Signal output pin.
    *   [/] When Emergency is detected, send a defined signal on the Servo Trigger output pin.
*   [X] **MQTT Integration (Emergency & Unlock):**
    *   [X] Port/Keep WiFi connection logic.
    *   [X] Port/Keep MQTT connection logic.
    *   [X] Implement publishing to `campus/security/emergency` when the Emergency button is pressed.
    *   [X] Implement subscription to `campus/security/unlock`.
    *   [X] When an unlock message is received, send the trigger signal on the Servo Trigger output pin.
*   [X] **Mock RFID Generation:** Keep the logic to generate a mock RFID string upon detection (this data is *not* sent to ESP32, only the signal is).
*   [X] **Serial Logging:** Add robust serial logging for debugging sensor states and signal sending.

## Milestone 3: ESP32 Firmware Development (ESP-IDF & ESP-WHO)

**Goal:** Port existing logic to ESP-IDF, integrate ESP-WHO face detection, and adapt to receive signals from the Mega.

*   [ ] **ESP-IDF Environment Setup:**
    *   [ ] Install ESP-IDF toolchain.
    *   [ ] Create a new ESP-IDF project structure for the ESP32-CAM.
*   [ ] **Component Porting (Arduino -> ESP-IDF):**
    *   [ ] **WiFi:** Implement WiFi connection using ESP-IDF `esp_wifi` APIs.
    *   [ ] **MQTT:** Implement MQTT connection, subscription (`/emergency`), and publishing (`/session`) using ESP-IDF MQTT client (e.g., `esp-mqtt`).
    *   [ ] **Camera:** Initialize and configure the camera using the ESP-IDF camera driver (`esp_camera.h`). Implement image capture logic.
    *   [ ] **GPIO:** Configure input pins (Motion Signal In, RFID Signal In) and LED output pins using ESP-IDF `driver/gpio`.
    *   [ ] **State Machine:** Port the state machine logic using FreeRTOS tasks and event groups/queues for handling state transitions and events (signals from Mega, MQTT messages, timeouts).
*   [ ] **ESP-WHO Face Detection Integration:**
    *   [ ] Add ESP-WHO components to the ESP-IDF project.
    *   [ ] Implement face detection logic within the `FACE_DETECTING` state using ESP-WHO functions on the captured image frame.
    *   [ ] Optimize image capture settings (resolution, quality) for face detection if needed.
*   [ ] **Input Signal Handling (ESP-IDF):**
    *   [ ] Implement GPIO interrupt handlers or a dedicated task to monitor the Motion Signal and RFID Signal input pins from the Mega.
    *   [ ] Use FreeRTOS mechanisms (queues, event groups) to notify the main state machine task when signals are received.
*   [ ] **State Machine Update (ESP-IDF):**
    *   [ ] Modify state transitions (`IDLE --> CONNECTION`, `RFID_WAITING --> SESSION`) to be triggered by events generated from the Mega's input signals.
    *   [ ] Modify the `FACE_DETECTING` state to trigger the transition based on ESP-WHO face detection result OR timeout.
    *   [ ] Ensure the `rfidDetected` status is correctly updated based on the Mega's signal event.
    *   [ ] Keep the EMERGENCY state logic triggered by `/emergency` MQTT messages.
*   [ ] **Remove Old Logic:** Ensure no residual Arduino framework code for motion sensing or `/rfid` subscription remains.
*   [ ] **Session Payload:** Update the `/session` MQTT payload publishing logic (using ESP-IDF MQTT client and JSON library like cJSON) to include:
    *   `rfid_detected`: based on the signal received from the Mega.
    *   `face_detected`: based on the result from ESP-WHO face detection.
*   [ ] **Logging:** Implement logging using ESP-IDF logging framework (`esp_log.h`).

## Milestone 4: Arduino Uno Servo Control Firmware

**Goal:** Implement the firmware for the dedicated Arduino Uno controlling the servo.

*   [ ] **Project Setup:** Create PlatformIO project for Arduino Uno.
*   [ ] **Pin Definitions:** Define input pin for Servo Trigger (from Mega) and output pin for Servo Control.
*   [ ] **Servo Library:** Include and initialize the Servo library.
*   [ ] **Trigger Logic:**
    *   [ ] Monitor the Servo Trigger input pin.
    *   [ ] When the trigger signal is received from the Mega, actuate the servo motor (e.g., move to unlocked position, wait, move back to locked position).
*   [ ] **Serial Logging:** Add serial logging for debugging trigger reception and servo action.


## Milestone 5: Integration Testing & Refinement

**Goal:** Test the complete system flow with the new ESP-IDF based firmware and refine timings/logic.

*   [ ] **Mega -> ESP32 Signal Test:** Verify the ESP32 (running ESP-IDF) correctly detects motion and RFID signals sent by the Mega.
*   [ ] **Mega -> Uno -> Servo Test:** Verify the Mega correctly triggers the Uno, and the Uno actuates the servo.
*   [ ] **ESP32 Face Detection Test:** Verify ESP-WHO successfully detects faces under reasonable conditions.
*   [ ] **End-to-End Session Test (with Face Detection):**
    *   [ ] Trigger motion -> Verify Mega signals ESP32 -> Verify ESP32 (ESP-IDF) connects & enters FACE_DETECTING -> Present face -> Verify face detected -> Verify ESP32 transitions -> Trigger RFID -> Verify Mega signals ESP32 -> Verify ESP32 sends session payload with `face_detected: true`, `rfid_detected: true`.
    *   [ ] Repeat variations (no face detected, no RFID signal received, timeouts) and verify `face_detected` and `rfid_detected` flags in the payload are correct.
*   [ ] **End-to-End Emergency Test:** Press Emergency button -> Verify Mega sends MQTT message -> Verify Mega triggers Servo Uno -> Verify ESP32 (ESP-IDF) enters EMERGENCY state.
*   [ ] **End-to-End Unlock Test:** Publish to `/unlock` topic -> Verify Mega receives message -> Verify Mega triggers Servo Uno.
*   [ ] **Performance & Timing:** Monitor ESP32 performance (memory usage, task timing with ESP-IDF tools) and refine timeouts/delays as needed.
*   [ ] **Documentation Update:** Final review and update of all READMEs based on implementation details.

---

**Future Considerations (Post Milestones):**
*   Multi-Session Management (if required).
*   Sending actual RFID data from Mega to ESP32 (requires Serial/UART communication instead of simple digital signal).
*   Implementing Face Recognition (embedding generation & comparison) - likely requires coordination with the backend API.
