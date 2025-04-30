#include <Arduino.h>

// --- Configuration ---
// Inputs from Sensors
const int MOTION_SENSOR_PIN = 5;
const int RFID_SENSOR_PIN = 6;

// Outputs to ESP32 (via Voltage Divider)
const int MOTION_SIGNAL_OUTPUT_PIN = 8;
const int RFID_SIGNAL_OUTPUT_PIN = 9;

// RFID Logic
const unsigned long RFID_ACTIVITY_TIMEOUT_MS = 1000; // Consider RFID stopped if pin 6 stays LOW for this long

const long DEBUG_BAUD_RATE = 115200;

// --- Global Variables ---
bool rfidSignalActive = false;         // Is the RFID output signal (Pin 9) currently HIGH?
unsigned long lastRfidPinHighTime = 0; // Timestamp of the last time Pin 6 read HIGH

int lastMotionState = LOW;
int lastRfidInputState = LOW;

void setup()
{
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    Serial.println("\n--- Mega GPIO Integration Test --- ");
    Serial.print("Motion Input Pin: ");
    Serial.println(MOTION_SENSOR_PIN);
    Serial.print("RFID Input Pin: ");
    Serial.println(RFID_SENSOR_PIN);
    Serial.print("Motion Output Pin: ");
    Serial.println(MOTION_SIGNAL_OUTPUT_PIN);
    Serial.print("RFID Output Pin: ");
    Serial.println(RFID_SIGNAL_OUTPUT_PIN);

    // Configure Inputs
    pinMode(MOTION_SENSOR_PIN, INPUT); 
    pinMode(RFID_SENSOR_PIN, INPUT);   

    // Configure Outputs
    pinMode(MOTION_SIGNAL_OUTPUT_PIN, OUTPUT);
    pinMode(RFID_SIGNAL_OUTPUT_PIN, OUTPUT);

    // Initialize outputs LOW
    digitalWrite(MOTION_SIGNAL_OUTPUT_PIN, LOW);
    digitalWrite(RFID_SIGNAL_OUTPUT_PIN, LOW);

    Serial.println("Outputs initialized LOW.");
}

void loop()
{
    // print the state of the pin that is writing to the esp32 rfid
    Serial.print("RFID Output Pin State: ");
    Serial.println(digitalRead(RFID_SIGNAL_OUTPUT_PIN));
    unsigned long currentTime = millis();

    // --- Handle Motion Sensor --- (Simple HIGH/LOW mapping)
    int currentMotionState = digitalRead(MOTION_SENSOR_PIN);
    if (currentMotionState != lastMotionState)
    {
        digitalWrite(MOTION_SIGNAL_OUTPUT_PIN, currentMotionState); // Directly map input to output
        Serial.print("Motion Input (Pin 5) changed to ");
        Serial.print(currentMotionState == HIGH ? "HIGH" : "LOW");
        Serial.print(", Output (Pin 8) set to ");
        Serial.println(currentMotionState == HIGH ? "HIGH" : "LOW");
        lastMotionState = currentMotionState;
    }

    // --- Handle RFID Sensor (Activity Timeout Logic) ---
    int currentRfidInputState = digitalRead(RFID_SENSOR_PIN);

    if (currentRfidInputState == HIGH)
    {
        // Pin 6 is HIGH - this means activity is present or ongoing
        lastRfidPinHighTime = currentTime; // Keep resetting the timeout timer

        if (!rfidSignalActive)
        {
            // If output signal wasn't already active, turn it on
            Serial.println("-> RFID Input (Pin 6) HIGH, Activating Output (Pin 9)");
            digitalWrite(RFID_SIGNAL_OUTPUT_PIN, HIGH);
            rfidSignalActive = true;
        }
    }
    else
    { // currentRfidInputState is LOW
        if (rfidSignalActive)
        {
            // Only check for timeout if the output signal was previously active
            if (currentTime - lastRfidPinHighTime >= RFID_ACTIVITY_TIMEOUT_MS)
            {
                // Timeout expired - pin 6 has been LOW for long enough
                Serial.println("-> RFID Input (Pin 6) Timeout, Deactivating Output (Pin 9)");
                digitalWrite(RFID_SIGNAL_OUTPUT_PIN, LOW);
                rfidSignalActive = false;
            }
            // else - it's LOW, but the timeout hasn't expired yet
        }
        // else - it's LOW and output was already inactive, do nothing
    }

    // Optional small delay
    delay(10); // Check inputs frequently
}