#include "serial_handler.h"
#include "../config.h"

// Define Serial ports (moved from main.cpp for encapsulation)
// We only need Serial2 for ESP32 communication according to current design
HardwareSerial &ESP32Serial = Serial2;
// HardwareSerial& MKRSerial = Serial1; // Removed as MKR comms seem deprecated

/**
 * Initialize the serial handler (called from main setup)
 */
void setupSerialHandler()
{
    // Initialization of Serial ports (Serial.begin) should happen in main setup()
    // This function could be used for other handler-specific setup if needed.
    // Serial.println(F("Serial Handler Initialized (ports configured in main setup)."));
    // No action needed here currently, ports are initialized in main setup.
}

/**
 * Sends the motion detected signal ('<M>') to the ESP32 via Serial2.
 */
void sendMotionDetected()
{
    Serial.println(F("SERIAL_HANDLER: Sending <M> to ESP32"));
    ESP32Serial.print("<M>");
}

/**
 * Sends the RFID detected signal ('<R[tag]>') to the ESP32 via Serial2.
 * Uses the MOCK_RFID_TAG defined in config.h.
 */
void sendRfidDetected()
{
    Serial.print(F("SERIAL_HANDLER: Sending <R" MOCK_RFID_TAG "> to ESP32..."));
    ESP32Serial.print("<R");
    ESP32Serial.print(MOCK_RFID_TAG);
    ESP32Serial.print(">");
    Serial.println(F(" Done."));
}

/**
 * Sends the emergency signal ('<E>') to the ESP32 via Serial2.
 * NOTE: Current main.cpp logic does NOT call this function.
 * Emergency is handled locally by triggering the servo pulse.
 */
void sendEmergencySignal()
{
    Serial.println(F("SERIAL_HANDLER: Sending <E> to ESP32"));
    ESP32Serial.print("<E>");
}

/**
 * Checks for and processes unlock commands potentially received from MKR.
 * Returns true if an unlock command was received and processed, false otherwise.
 * NOTE: Currently seems unused as MKR communication appears removed.
 */
/*
bool checkForUnlockCommand() {
    if (MKRSerial.available() > 0) {
        String command = MKRSerial.readStringUntil('\n');
        command.trim(); // Remove potential whitespace/newlines
        Serial.print(F("Received from MKR: ")); Serial.println(command);

        if (command.equalsIgnoreCase("UNLOCK")) {
            Serial.println(F("UNLOCK command received from MKR."));
            // Directly trigger servo pulse here, similar to emergency logic
            Serial.println(F("  -> Triggering Servo Pulse..."));
            digitalWrite(SERVO_TRIGGER_OUT_PIN, HIGH);
            delay(SERVO_TRIGGER_DURATION_MS); // Keep pin HIGH
            digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
            Serial.println(F("  -> Servo Pulse Complete."));
            return true;
        } else {
            Serial.println(F("Unknown command from MKR."));
        }
    }
    return false;
}
*/