#include <Arduino.h>

// --- Configuration ---
const int RFID_INPUT_PIN = 19;
const long DEBUG_BAUD_RATE = 115200;

// --- Global Variables ---
int lastPinState = -1; // Initialize to an invalid state to trigger first print

void setup()
{
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    delay(2000); // Give time to open monitor
    Serial.println("\n--- ESP32 GPIO RFID Signal Test Receiver ---");
    Serial.print("Monitoring Pin ");
    Serial.print(RFID_INPUT_PIN);
    Serial.println(" (configured as INPUT_PULLDOWN)");

    // Configure pin as INPUT_PULLDOWN
    pinMode(RFID_INPUT_PIN, INPUT_PULLDOWN);

    // Read initial state immediately after setup
    lastPinState = digitalRead(RFID_INPUT_PIN);
    Serial.print("Initial state: ");
    Serial.println(lastPinState == HIGH ? "HIGH" : "LOW");
}

void loop()
{
    int currentPinState = digitalRead(RFID_INPUT_PIN);

    if (currentPinState != lastPinState)
    {
        Serial.print("RFID Signal state changed to: ");
        Serial.println(currentPinState == HIGH ? "HIGH" : "LOW");
        lastPinState = currentPinState;
    }

    // Small delay to prevent spamming the serial monitor too quickly
    delay(50);
}