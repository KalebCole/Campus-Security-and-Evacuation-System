#include <Arduino.h>

// --- Configuration ---
const int MOTION_OUTPUT_PIN = 8;
const int RFID_OUTPUT_PIN = 9;

const unsigned long MOTION_TOGGLE_DELAY_MS = 4000; // Toggle motion every 4 seconds
const unsigned long RFID_TOGGLE_DELAY_MS = 6000;   // Toggle RFID every 6 seconds (different timing)

const long DEBUG_BAUD_RATE = 115200;

// --- Global Variables ---
int motionPinState = LOW;
int rfidPinState = LOW;
unsigned long lastMotionToggleTime = 0;
unsigned long lastRfidToggleTime = 0;

void setup()
{
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    Serial.println("\n--- Mega GPIO Motion & RFID Signal Test Sender ---");
    Serial.print("Toggling Motion Pin ");
    Serial.print(MOTION_OUTPUT_PIN);
    Serial.print(" every ");
    Serial.print(MOTION_TOGGLE_DELAY_MS);
    Serial.println(" ms");
    Serial.print("Toggling RFID Pin ");
    Serial.print(RFID_OUTPUT_PIN);
    Serial.print(" every ");
    Serial.print(RFID_TOGGLE_DELAY_MS);
    Serial.println(" ms");

    pinMode(MOTION_OUTPUT_PIN, OUTPUT);
    pinMode(RFID_OUTPUT_PIN, OUTPUT);

    digitalWrite(MOTION_OUTPUT_PIN, motionPinState); // Start LOW
    digitalWrite(RFID_OUTPUT_PIN, rfidPinState);     // Start LOW

    lastMotionToggleTime = millis();
    lastRfidToggleTime = millis(); // Stagger initial toggle slightly if desired

    Serial.println("Starting states: LOW");
}

void loop()
{
    unsigned long currentTime = millis();

    // Toggle Motion Pin
    if (currentTime - lastMotionToggleTime >= MOTION_TOGGLE_DELAY_MS)
    {
        motionPinState = !motionPinState;
        digitalWrite(MOTION_OUTPUT_PIN, motionPinState);
        lastMotionToggleTime = currentTime;
        Serial.print("Pin ");
        Serial.print(MOTION_OUTPUT_PIN);
        Serial.print(" (Motion) state changed to: ");
        Serial.println(motionPinState == HIGH ? "HIGH" : "LOW");
    }

    // Toggle RFID Pin
    if (currentTime - lastRfidToggleTime >= RFID_TOGGLE_DELAY_MS)
    {
        rfidPinState = !rfidPinState;
        digitalWrite(RFID_OUTPUT_PIN, rfidPinState);
        lastRfidToggleTime = currentTime;
        Serial.print("Pin ");
        Serial.print(RFID_OUTPUT_PIN);
        Serial.print(" (RFID) state changed to: ");
        Serial.println(rfidPinState == HIGH ? "HIGH" : "LOW");
    }
}