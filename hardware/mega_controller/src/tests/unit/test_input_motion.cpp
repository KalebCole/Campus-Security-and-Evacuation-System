#include "../../config.h"
#include <Arduino.h>

// --- Test Configuration ---
// Goal: Detect Motion signal (Pin 5, Active HIGH).
// Method: Consider motion active as long as pin reads HIGH. If pin stays LOW
//         for longer than MOTION_ACTIVITY_TIMEOUT_MS, consider it stopped.

// --- Constants ---
// How long the pin must remain LOW before we declare motion stopped (ms)
// PIR sensors often have their own hold time, so this can be relatively short,
// just long enough to bridge potential brief LOW dips during detection.
const unsigned long MOTION_ACTIVITY_TIMEOUT_MS = 2000; // e.g., 2 seconds

// --- Global Variables ---
bool motionActive = false;      // Is motion currently considered active?
unsigned long lastHighTime = 0; // Timestamp of the last time the pin read HIGH

void setup()
{
    Serial.begin(DEBUG_SERIAL_BAUD);
    while (!Serial)
        ;
    Serial.println(F("\n--- Test: Motion Input Detection (Activity Timeout) ---"));
    Serial.print(F("Timeout duration: "));
    Serial.print(MOTION_ACTIVITY_TIMEOUT_MS);
    Serial.println(F(" ms"));
    Serial.println(F("Expected Behavior: Idle=LOW(0), Detected=HIGH Activity"));

    // Set Motion sensor pin mode
    pinMode(MOTION_SENSOR_PIN, INPUT);
    Serial.print(F("Motion Pin ("));
    Serial.print(MOTION_SENSOR_PIN);
    Serial.println(F(") configured as INPUT."));

    // Read initial state
    int initialReading = digitalRead(MOTION_SENSOR_PIN);
    Serial.print(F("Initial Motion Pin State: "));
    Serial.println(initialReading);
    if (initialReading == HIGH)
    {
        // If it starts HIGH, immediately mark as active
        motionActive = true;
        lastHighTime = millis();
        Serial.println(F("WARNING: Pin started HIGH, assuming active."));
    }
}

void loop()
{
    int currentReading = digitalRead(MOTION_SENSOR_PIN);

    if (currentReading == HIGH)
    {
        // Pin is HIGH - motion detected or ongoing
        lastHighTime = millis(); // Keep resetting the timeout timer

        if (!motionActive)
        {
            // If it wasn't already active, this is the start of detection
            Serial.println(F("-> Motion DETECTED (Activity Started)"));
            motionActive = true;
        }
        // else - it's still active, do nothing extra
    }
    else
    {
        // Pin is LOW - check if it's been LOW long enough to time out
        if (motionActive)
        {
            // Only check for timeout if it was previously active
            if (millis() - lastHighTime >= MOTION_ACTIVITY_TIMEOUT_MS)
            {
                // Timeout expired - pin has been LOW for long enough
                Serial.println(F("-> Motion Stopped (Timeout)"));
                motionActive = false;
            }
            // else - it's LOW, but the timeout hasn't expired yet
        }
        // else - it's LOW and was already inactive, do nothing
    }

    // Optional small delay
    // delay(1);
}