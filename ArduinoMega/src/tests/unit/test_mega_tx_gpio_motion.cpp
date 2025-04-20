#include <Arduino.h>

// --- Configuration ---
const int MOTION_OUTPUT_PIN = 8;
const unsigned long TOGGLE_DELAY_MS = 2000; // Toggle every 2 seconds
const long DEBUG_BAUD_RATE = 115200;

// --- Global Variables ---
int pinState = LOW;
unsigned long lastToggleTime = 0;

void setup()
{
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    Serial.println("\n--- Mega GPIO Motion Signal Test Sender ---");
    Serial.print("Toggling Pin ");
    Serial.print(MOTION_OUTPUT_PIN);
    Serial.print(" every ");
    Serial.print(TOGGLE_DELAY_MS);
    Serial.println(" ms");

    pinMode(MOTION_OUTPUT_PIN, OUTPUT);
    digitalWrite(MOTION_OUTPUT_PIN, pinState); // Start LOW
    lastToggleTime = millis();
    Serial.println("Starting state: LOW");
}

void loop()
{
    unsigned long currentTime = millis();
    if (currentTime - lastToggleTime >= TOGGLE_DELAY_MS)
    {
        pinState = !pinState; // Toggle state (HIGH -> LOW, LOW -> HIGH)
        digitalWrite(MOTION_OUTPUT_PIN, pinState);
        lastToggleTime = currentTime;

        Serial.print("Pin ");
        Serial.print(MOTION_OUTPUT_PIN);
        Serial.print(" state changed to: ");
        Serial.println(pinState == HIGH ? "HIGH" : "LOW");
    }
}