#include <Arduino.h>

// --- Configuration ---
const int MOTION_INPUT_PIN = 18;
const long DEBUG_BAUD_RATE = 115200;

// --- Global Variables ---
int lastPinState = -1; // Initialize to an invalid state to trigger first print

void setup()
{
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    delay(2000); // Give time to open monitor
    Serial.println("\n--- ESP32 GPIO Motion Signal Test Receiver ---");
    Serial.print("Monitoring Pin ");
    Serial.print(MOTION_INPUT_PIN);
    Serial.println(" (configured as INPUT_PULLDOWN)");

    // Configure pin as INPUT_PULLDOWN
    // NOTE: INPUT_PULLDOWN might require specific ESP32 IDF versions or board support.
    // If it fails to compile or doesn't work, INPUT_PULLUP might be needed,
    // requiring the Mega to actively drive LOW when inactive.
    pinMode(MOTION_INPUT_PIN, INPUT_PULLDOWN);

    // Read initial state immediately after setup
    lastPinState = digitalRead(MOTION_INPUT_PIN);
    Serial.print("Initial state: ");
    Serial.println(lastPinState == HIGH ? "HIGH" : "LOW");
}

void loop()
{
    int currentPinState = digitalRead(MOTION_INPUT_PIN);

    if (currentPinState != lastPinState)
    {
        Serial.print("Motion Signal state changed to: ");
        Serial.println(currentPinState == HIGH ? "HIGH" : "LOW");
        lastPinState = currentPinState;
    }

    // Small delay to prevent spamming the serial monitor too quickly
    // if the signal is noisy or bouncing.
    delay(50);
}