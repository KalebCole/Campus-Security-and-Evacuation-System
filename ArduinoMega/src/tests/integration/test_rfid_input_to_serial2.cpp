// integration test for the serial output
// we are reading from the rfid input on the mega and then generating a fake rfid tag
// we are then sending the fake rfid tag to the serial output

#include "../../config.h"
#include <Arduino.h>

// --- Test Configuration ---
// Goal: Detect RFID Activity (Pin 6, Active HIGH) using Activity Timeout method,
//       and upon *initial* detection, send 'R' + MOCK_RFID_TAG + '\0' via Serial2 (to ESP32).
// Method: Consider RFID active as long as pin reads HIGH. If pin stays LOW
//         for longer than RFID_ACTIVITY_TIMEOUT_MS, consider it stopped. Send Serial2 message ONLY
//         when activity starts.

// --- Constants ---
const unsigned long RFID_ACTIVITY_TIMEOUT_MS = 1000; // Consider RFID stopped if pin stays LOW for this long (ms)

// --- Global Variables ---
bool rfidActive = false;        // Is the RFID currently considered active?
unsigned long lastHighTime = 0; // Timestamp of the last time the pin read HIGH

void setup()
{
    Serial.begin(DEBUG_SERIAL_BAUD);
    while (!Serial)
        ;
    Serial.println(F("\n--- Test: RFID Input to Serial Output 'R' ---"));
    Serial.print(F("RFID Timeout duration: "));
    Serial.print(RFID_ACTIVITY_TIMEOUT_MS);
    Serial.println(F(" ms"));
    Serial.println(F("Expected Behavior: Idle=LOW(0), Detected=HIGH Activity"));

    // Initialize Serial2 for ESP32 communication
    Serial2.begin(ESP32_SERIAL_BAUD); // Use ESP32 baud rate from config
    Serial.print(F("Serial2 (ESP32) initialized at "));
    Serial.print(ESP32_SERIAL_BAUD);
    Serial.println(F(" baud."));

    // Set RFID pin mode - NO internal pull-up based on user request
    pinMode(RFID_SENSOR_PIN, INPUT);
    Serial.print(F("RFID Pin ("));
    Serial.print(RFID_SENSOR_PIN);
    Serial.println(F(") configured as INPUT."));

    // Read initial state
    int initialReading = digitalRead(RFID_SENSOR_PIN);
    Serial.print(F("Initial RFID Pin State: "));
    Serial.println(initialReading);
    if (initialReading == HIGH)
    {
        // If it starts HIGH, immediately mark as active but DON'T send initial tag here
        // Let the loop handle the first valid detection if it stays HIGH
        rfidActive = true;
        lastHighTime = millis();
        Serial.println(F("WARNING: Pin started HIGH, assuming active state initially."));
        // Maybe send tag on startup if HIGH? Depends on desired behaviour.
        // For now, only sending on transition from LOW->HIGH detected in loop.
    }
    Serial.println(F("--- Setup Complete - Waiting for RFID Activity ---"));
}

void loop()
{
    int currentReading = digitalRead(RFID_SENSOR_PIN);

    if (currentReading == HIGH)
    {
        // Pin is HIGH - this means activity is present or ongoing
        lastHighTime = millis(); // Keep resetting the timeout timer

        if (!rfidActive)
        {
            // If it wasn't already active, this is the start of detection
            rfidActive = true; // Set state FIRST
            Serial.println(F("-> RFID DETECTED (Activity Started)"));

            // NOW, send the serial message to ESP32
            Serial.print(F("   -> Sending 'R' + tag '"));
            Serial.print(MOCK_RFID_TAG);
            Serial.println(F("' + \\0 to ESP32 via Serial2..."));
            Serial2.write('R');
            Serial2.print(MOCK_RFID_TAG);
            Serial2.write('\0'); // Null terminator
            Serial.println(F("   -> Message Sent."));
        }
        // else - it's still active, do nothing extra (don't resend tag)
    }
    else
    {
        // Pin is LOW - check if it's been LOW long enough to time out
        if (rfidActive)
        {
            // Only check for timeout if it was previously active
            if (millis() - lastHighTime >= RFID_ACTIVITY_TIMEOUT_MS)
            {
                // Timeout expired - pin has been LOW for long enough
                Serial.println(F("-> RFID Stopped (Timeout)"));
                rfidActive = false;
            }
            // else - it's LOW, but the timeout hasn't expired yet
        }
        // else - it's LOW and was already inactive, do nothing
    }

    // Optional small delay
    // delay(1);
}