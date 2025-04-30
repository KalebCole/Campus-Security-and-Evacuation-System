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
