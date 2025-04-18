#include <Arduino.h>
#include "config.h"
#include "serial_handler/serial_handler.h" // Include the serial handler

// --- Serial Port Assignments ---
// References removed - Now managed internally by serial_handler.cpp
// Serial port initialization (SerialX.begin()) remains here.
// --- End Serial Port Assignments ---

void setup()
{
    // 1. Initialize Debug Serial (Serial Monitor via USB)
    Serial.begin(DEBUG_SERIAL_BAUD);
    while (!Serial)
        ;
    Serial.println(F("\n--- Arduino Mega Sensor Hub Initializing ---"));

    // 2. Initialize Communication Serial Port (ESP32 only)
    // Serial1.begin(MKR_SERIAL_BAUD);    // Removed - No Serial1 communication
    Serial2.begin(ESP32_SERIAL_BAUD); // Initialize Serial2 for ESP32
    Serial.println(F("Hardware Serial Ports Initialized:"));
    // Serial.print(F("  - Serial1 (MKR) Baud: ")); Serial.println(MKR_SERIAL_BAUD); // Removed
    Serial.print(F("  - Serial2 (ESP32) Baud: "));
    Serial.println(ESP32_SERIAL_BAUD);

    // 3. Initialize the Serial Handler module
    setupSerialHandler();

    // 4. Initialize Pin Modes
    pinMode(MOTION_SENSOR_PIN, INPUT);
    pinMode(RFID_SENSOR_PIN, INPUT_PULLUP);
    pinMode(EMERGENCY_PIN, INPUT);
    pinMode(SERVO_TRIGGER_OUT_PIN, OUTPUT);
    digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW); // Ensure servo trigger starts LOW
    Serial.println(F("Pin modes set."));      // Simplified pin mode logging

    Serial.println(F("--- Setup Complete ---"));
}

// Global variables for sensor states and debounce timing
int motionState = LOW;
int lastMotionState = LOW;
unsigned long lastMotionDebounceTime = 0;

int rfidState = HIGH; // Assuming pull-up, LOW is active
int lastRfidState = HIGH;
unsigned long lastRfidDebounceTime = 0;

int emergencyState = HIGH; // Assuming LOW is active
int lastEmergencyState = HIGH;
unsigned long lastEmergencyDebounceTime = 0;

// Flag to indicate if emergency has occurred (to stop other signals)
bool emergencyActive = false;

void loop()
{
    // --- Check for Emergency FIRST ---
    // Read emergency button state
    int readingEmergency = digitalRead(EMERGENCY_PIN);

    // Emergency Button Debounce (Active LOW)
    if (readingEmergency != lastEmergencyState)
    {
        lastEmergencyDebounceTime = millis();
    }
    if ((millis() - lastEmergencyDebounceTime) > SENSOR_DEBOUNCE_TIME_MS)
    {
        if (readingEmergency != emergencyState)
        {
            emergencyState = readingEmergency;
            if (emergencyState == LOW)
            {
                if (!emergencyActive)
                { // Trigger only once
                    Serial.println(F("** EMERGENCY DETECTED **"));
                    emergencyActive = true; // Set flag
                    // No serial signal sent ('E' removed)
                    // Trigger Servo Pulse for Uno (Pin 4 -> Uno Pin 5)
                    Serial.println(F("  -> Triggering Servo Pulse..."));
                    digitalWrite(SERVO_TRIGGER_OUT_PIN, HIGH);
                    delay(SERVO_TRIGGER_DURATION_MS); // Keep pin HIGH for specified duration
                    digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
                    Serial.println(F("  -> Servo Pulse Complete."));
                }
            }
            else
            {
                if (emergencyActive)
                { // Log release only if it was active
                    Serial.println(F("Emergency released."));
                    emergencyActive = false; // Reset flag
                }
            }
        }
    }
    lastEmergencyState = readingEmergency;

    // --- Process other sensors ONLY if NO emergency is active ---
    if (!emergencyActive)
    {
        // Read current sensor values
        int readingMotion = digitalRead(MOTION_SENSOR_PIN);
        int readingRfid = digitalRead(RFID_SENSOR_PIN); // Assumes Active HIGH now

        // Motion Sensor Debounce (Active HIGH)
        if (readingMotion != lastMotionState)
        {
            lastMotionDebounceTime = millis();
        }
        if ((millis() - lastMotionDebounceTime) > SENSOR_DEBOUNCE_TIME_MS)
        {
            if (readingMotion != motionState)
            {
                motionState = readingMotion;
                if (motionState == HIGH)
                {
                    Serial.println(F("** Motion DETECTED **"));
                    sendMotionDetected(); // Send 'M' to ESP32 via Serial2
                }
                else
                {
                    Serial.println(F("Motion stopped."));
                    // Optional: Send a 'motion stopped' signal?
                }
            }
        }
        lastMotionState = readingMotion;

        // RFID Sensor Debounce (Active HIGH)
        if (readingRfid != lastRfidState)
        {
            lastRfidDebounceTime = millis();
        }
        if ((millis() - lastRfidDebounceTime) > SENSOR_DEBOUNCE_TIME_MS)
        {
            if (readingRfid != rfidState)
            {
                rfidState = readingRfid;
                if (rfidState == HIGH)
                { // Changed to HIGH for Active HIGH RFID
                    Serial.println(F("** RFID DETECTED **"));
                    sendRfidDetected(); // Send 'R' + tag to ESP32 via Serial2
                }
                else
                {
                    Serial.println(F("RFID stopped."));
                }
            }
        }
        lastRfidState = readingRfid;

    } // End of if(!emergencyActive)

    // --- Check for Commands from MKR --- (Removed - No Serial1/MKR comms)
    // if (checkForUnlockCommand()) { ... }
}   //     {
    //         motionState = readingMotion;
    //         if (motionState == HIGH)
    //         {
    //             Serial.println(F("** Motion DETECTED **"));
    //             // TODO: Call sendMotionDetected();
    //         }
    //         else
    //         {
    //             Serial.println(F("Motion stopped."));
    //         }
    //     }
    // }
    // lastMotionState = readingMotion;

    // // RFID Sensor Debounce (Active LOW)
    // if (readingRfid != lastRfidState)
    // {
    //     lastRfidDebounceTime = millis();
    // }
    // if ((millis() - lastRfidDebounceTime) > SENSOR_DEBOUNCE_TIME_MS)
    // {
    //     if (readingRfid != rfidState)
    //     {
    //         rfidState = readingRfid;
    //         if (rfidState == LOW)
    //         {
    //             Serial.println(F("** RFID DETECTED (on LOW) **"));
    //             // TODO: Call sendRfidDetected();
    //         }
    //         else
    //         {
    //             Serial.println(F("** RFID NOT DETECTED (on HIGH) ** ."));
    //             // Optional: Log when RFID goes HIGH again
    //             // Serial.println(F("RFID stopped."));
    //         }
    //     }
    // }
    // lastRfidState = readingRfid;

    // // Emergency Button Debounce (Active LOW)
    // if (readingEmergency != lastEmergencyState)
    // {
    //     lastEmergencyDebounceTime = millis();
    // }
    // if ((millis() - lastEmergencyDebounceTime) > SENSOR_DEBOUNCE_TIME_MS)
    // {
    //     if (readingEmergency != emergencyState)
    //     {
    //         emergencyState = readingEmergency;
    //         if (emergencyState == HIGH)
    //         {
    //              Serial.println(F("** EMERGENCY DETECTED **"));
    //             sendEmergencySignal(); // Send 'E' to MKR WiFi 1010 via Serial1

    //             // Trigger Servo Pulse for Uno (Pin 4 -> Uno Pin 5)
    //             Serial.println(F("  -> Triggering Servo Pulse..."));
    //             digitalWrite(SERVO_TRIGGER_OUT_PIN, HIGH);
    //             delay(SERVO_TRIGGER_DURATION_MS); // Keep pin HIGH for specified duration
    //             digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
    //             Serial.println(F("  -> Servo Pulse Complete."));
    //         }
    //         else
    //         {
    //             Serial.println(F("Emergency released."));
    //         }
    //     }
    // }
    // lastEmergencyState = readingEmergency;

    // --- Check for Commands from MKR --- (Placeholder Logic)

    // TODO: Call checkForUnlockCommand() and trigger servo if true

    // Small delay to prevent busy-waiting (optional)
    // delay(1); // Use cautiously, non-blocking preferred
}
            }
        }
        lastRfidState = readingRfid;

    } // End of if(!emergencyActive)

    // --- Check for Commands from MKR --- (Removed - No Serial1/MKR comms)
    // if (checkForUnlockCommand()) { ... }
}