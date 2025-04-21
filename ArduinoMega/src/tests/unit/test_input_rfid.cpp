#include <Arduino.h>
#include "../../config.h" // Include config from parent src directory

// --- Test Configuration ---
// Goal: Detect RFID signal which is IDLE=LOW(0), Detected=Activity (pin reads HIGH).
// Method: Consider RFID active as long as pin reads HIGH. If pin stays LOW
//         for longer than RFID_ACTIVITY_TIMEOUT_MS, consider it stopped.

// --- Constants ---
const unsigned long RFID_ACTIVITY_TIMEOUT_MS = 1000; // Consider RFID stopped if pin stays LOW for this long (ms)

// --- Global Variables ---
bool rfidActive = false;        // Is the RFID currently considered active?
unsigned long lastHighTime = 0; // Timestamp of the last time the pin read HIGH

void setup()
{
    Serial.begin(DEBUG_SERIAL_BAUD); // Use baud rate from config
    while (!Serial)
        ;
    Serial.println(F("\n--- Test: RFID Input Detection (Activity Timeout) ---"));
    Serial.print(F("Timeout duration: "));
    Serial.print(RFID_ACTIVITY_TIMEOUT_MS);
    Serial.println(F(" ms"));
    Serial.println(F("Expected Behavior: Idle=LOW(0), Detected=HIGH Activity"));

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
        // If it starts HIGH for some reason, immediately mark as active
        rfidActive = true;
        lastHighTime = millis();
        Serial.println(F("WARNING: Pin started HIGH, assuming active."));
    }
}

void loop()
{
    int currentReading = digitalRead(RFID_SENSOR_PIN);
    // Serial.print(F("RFID Pin State: "));
    // Serial.println(currentReading);

    if (currentReading == HIGH)
    {

        // Pin is HIGH - this means activity is present or ongoing
        lastHighTime = millis(); // Keep resetting the timeout timer

        if (!rfidActive)
        {
            // If it wasn't already active, this is the start of detection
            Serial.println(F("-> RFID DETECTED (Activity Started)"));
            rfidActive = true;
            // send fake rfid data from the mock
            Serial.println(F("-> Sending fake RFID data"));
            // print the mock rfid from the config
            Serial.print(F("Mock RFID: "));
            Serial.println(MOCK_RFID_TAG);
        }
        // else - it's still active, do nothing extra
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