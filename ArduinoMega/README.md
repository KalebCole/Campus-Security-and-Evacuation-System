# Arduino Mega - Sensor Hub & Signal Router Firmware

## Overview

This firmware runs on the Arduino Mega, which serves as the central sensor hub and signal coordinator for the Campus Security Enhancement System (CSES). Its primary responsibilities include:

*   Reading input from the Motion Sensor (Pin 5, Active HIGH), RFID Sensor (Pin 6, Active HIGH), and Emergency Button (Pin 7, Active LOW).
*   Transmitting sensor events ('M' for motion, 'R<tag>' for RFID) to the ESP32-CAM over `Serial2` (TX Pin 16, RX Pin 17).
*   Generating a digital trigger signal output (Pin 4, HIGH pulse) to the Arduino Uno (Servo Controller) based *only* on Emergency Button presses.
*   Providing status logging via the main `Serial` interface for debugging.

Network connectivity (WiFi/MQTT) is handled entirely by other system components (ESP32, API), not the Mega.

## Features

*   **Sensor Integration:** Reads digital states from Motion (HIGH), RFID (HIGH), and Emergency Button (LOW) sensors with debouncing.
*   **Serial Communication (to ESP32 via `Serial2`):**
    *   Sends `M` character upon motion detection.
    *   Generates a mock RFID tag and sends `R` followed by the tag string (null-terminated) upon RFID detection.
    *   Uses Mega Pins TX2 (16) / RX2 (17). **Note:** Corresponding ESP32 pins need configuration.
*   **Servo Trigger Signal (to Uno):** Sends a timed `HIGH` pulse on Pin 4 to trigger servo actuation on the connected Arduino Uno *only* when an emergency is detected.
*   **Serial Logging:** Outputs status, sensor readings, serial activity, and errors to the `Serial` monitor for debugging.

## Configuration

All user-configurable parameters should be defined in `src/config.h`:

*   **Pin Definitions:**
    *   Inputs: `MOTION_SENSOR_PIN` (5), `RFID_SENSOR_PIN` (6), `EMERGENCY_PIN` (7).
    *   Outputs: `SERVO_TRIGGER_OUT_PIN` (4).
    *   Serial2 (ESP32): `ESP32_SERIAL_TX_PIN` (16), `ESP32_SERIAL_RX_PIN` (17).
*   **Serial Configuration:**
    *   `DEBUG_SERIAL_BAUD` (e.g., 115200 for `Serial`).
    *   `ESP32_SERIAL_BAUD` (e.g., 9600 for `Serial2`).
*   **Timing Constants:**
    *   `SENSOR_DEBOUNCE_TIME_MS` (e.g., 50 - *May require tuning*).
    *   `SERVO_TRIGGER_DURATION_MS` (e.g., 100 - *May require tuning*).
*   **Mock RFID Value:**
    *   `MOCK_RFID_TAG` (e.g., `"FAKE123"`).

**Important:** Ensure you verify pin assignments and potentially tune timing constants in `src/config.h` before compiling and uploading.

## Dependencies

*   **Hardware:**
    *   Arduino Mega 2560 (or compatible)
    *   Motion Sensor (Digital Output, HIGH on detection)
    *   RFID Reader (Digital Output, Active HIGH detection)
    *   Emergency Button (Digital Output, LOW on detection)
    *   ESP32-CAM (or other device for receiving `Serial2` data)
    *   Arduino Uno (or other device for receiving servo trigger on Pin 5 from Mega Pin 4)
*   **Libraries (Managed by PlatformIO):**
    *   Standard Arduino libraries (`Arduino.h`, `HardwareSerial.h`)
*   **Development Environment:**
    *   [PlatformIO IDE](https://platformio.org/)

## Setup & Flashing

1.  **Clone/Open Project:** Open this project folder (`ArduinoMega`) in VS Code with the PlatformIO extension installed.
2.  **Configure:** Edit `src/config.h` to set your correct pin assignments and desired timing/serial parameters.
3.  **Build:** Use the PlatformIO `Build` command (Checkmark icon in the status bar or `Ctrl+Alt+B`).
4.  **Upload:** Connect the Arduino Mega via USB and use the PlatformIO `Upload` command (Right arrow icon in the status bar or `Ctrl+Alt+U`).
5.  **Monitor:** Use the PlatformIO `Serial Monitor` command (Plug icon in the status bar or `Ctrl+Alt+S`) with the configured `DEBUG_SERIAL_BAUD` rate (e.g., 115200) to view log output.

## Operation

Once flashed and powered, the Mega runs a continuous loop:

1.  Initializes `Serial` (debug) and `Serial2` (ESP32) communication.
2.  Configures input pins (Motion, RFID, Emergency) and output pin (Servo Trigger).
3.  Enters the main `loop()`:
    *   **Reads Sensors:** Reads the digital state of the Motion, RFID, and Emergency pins, applying debouncing logic.
    *   **Motion Detection:** If debounced motion is detected (Pin 5 HIGH), sends `'M'` via `Serial2`.
    *   **RFID Detection:** If debounced RFID is detected (Pin 6 HIGH), sends `'R'` followed by the `MOCK_RFID_TAG` string and a null terminator (` `) via `Serial2`.
    *   **Emergency Detection:** If debounced emergency is detected (Pin 7 LOW):
        *   Stops sending Motion/RFID signals (if currently active).
        *   Activates `SERVO_TRIGGER_OUT_PIN` (Pin 4) HIGH for `SERVO_TRIGGER_DURATION_MS`.
    *   **Logging:** Outputs relevant actions and sensor states to the `Serial` monitor.

## ✅ Testing Plan & TODOs

To test the firmware incrementally, build and run the following environments using PlatformIO:

**I. Component Tests (Using scripts in `src/tests/`)**

-   [ ] **`env:test_motion_input`**:
    -   **Goal:** Verify Mega reads and debounces Motion sensor (Pin 5, Active HIGH).
    -   **Action:** Upload using `pio run -e test_motion_input -t upload`. Open Serial Monitor. Trigger motion sensor HIGH.
    -   **Verify:** Serial Monitor prints "** Motion DETECTED **" only once per stable HIGH signal, and "Motion stopped." when LOW.
-   [ ] **`env:test_rfid_input`**:
    -   **Goal:** Verify Mega reads and debounces RFID sensor (Pin 6, Active HIGH).
    -   **Action:** Upload using `pio run -e test_rfid_input -t upload`. Open Serial Monitor. Trigger RFID sensor HIGH.
    -   **Verify:** Serial Monitor prints "** RFID DETECTED **" only once per stable HIGH signal, and "RFID stopped." when LOW.
-   [ ] **`env:test_emergency_input`**:
    -   **Goal:** Verify Mega reads and debounces Emergency button (Pin 7, Active LOW).
    -   **Action:** Upload using `pio run -e test_emergency_input -t upload`. Open Serial Monitor. Trigger Emergency button LOW.
    -   **Verify:** Serial Monitor prints "** EMERGENCY DETECTED **" only once per stable LOW signal, and "Emergency released." when HIGH.
-   [ ] **`env:test_serial_output_m`**:
    -   **Goal:** Verify Mega sends 'M' character via `Serial2` (Pin 16).
    -   **Action:** Upload using `pio run -e test_serial_output_m -t upload`. Program ESP32 with a receiver sketch. Open Serial Monitor. Send trigger command (e.g., 'm') via monitor.
    -   **Verify:** ESP32's monitor shows received 'M'. Mega's monitor shows confirmation.
-   [ ] **`env:test_serial_output_r`**:
    -   **Goal:** Verify Mega sends 'R' + tag + '\0' via `Serial2` (Pin 16).
    *   **Action:** Upload using `pio run -e test_serial_output_r -t upload`. Program ESP32 with a receiver sketch. Open Serial Monitor. Send trigger command (e.g., 'r') via monitor.
    *   **Verify:** ESP32's monitor shows received 'R' and the correct tag. Mega's monitor shows confirmation.
-   [ ] **`env:test_serial_output_e`**:
    -   **Goal:** Verify Mega sends 'E' character via `Serial2` (Pin 16) ***for test purposes***.
    -   **Action:** Upload using `pio run -e test_serial_output_e -t upload`. Program ESP32 with a receiver sketch. Open Serial Monitor. Send trigger command (e.g., 'e') via monitor.
    -   **Verify:** ESP32's monitor shows received 'E'. Mega's monitor shows confirmation.
-   [ ] **`env:test_servo_pulse_output`**:
    -   **Goal:** Verify Mega generates correct duration pulse on Pin 4.
    -   **Action:** Upload using `pio run -e test_servo_pulse_output -t upload`. Open Serial Monitor. Send trigger command (e.g., 'p') via monitor.
    -   **Verify:** Mega's monitor prints "Pulse starting...", "Pulse finished.", and "Actual duration: XXX ms" (where XXX is close to `SERVO_TRIGGER_DURATION_MS`).

**II. Link Tests (Using main code from `src/main.cpp`)**

-   [ ] **`env:test_mega_to_esp32_link`**:
    -   **Goal:** Verify Motion/RFID detection triggers serial messages received by ESP32.
    -   **Action:** Upload main code using `pio run -e test_mega_to_esp32_link -t upload`. Program ESP32 with receiver sketch. Trigger Motion and RFID sensors connected to Mega.
    -   **Verify:** ESP32 monitor shows received 'M' or 'R<tag>'.
-   [ ] **`env:test_mega_to_uno_link`**:
    -   **Goal:** Verify Emergency detection triggers servo movement on Uno (via Pin 4 pulse).
    -   **Action:** Upload main code using `pio run -e test_mega_to_uno_link -t upload`. Upload servo code to Uno. Trigger Emergency button on Mega.
    -   **Verify:** Uno servo moves to unlock, holds, then locks. Uno monitor shows trigger received.

**III. Integration Test (Using main code from `src/main.cpp`)**

-   [ ] **`env:test_emergency_preemption`**:
    -   **Goal:** Verify Emergency stops Motion/RFID transmission and triggers servo pulse.
    -   **Action:** Use `test_mega_to_esp32_link` setup. Trigger Motion/RFID. While signals are active, trigger Emergency button.
    -   **Verify:** 'M'/'R' messages stop arriving at ESP32. Uno servo performs unlock cycle.
