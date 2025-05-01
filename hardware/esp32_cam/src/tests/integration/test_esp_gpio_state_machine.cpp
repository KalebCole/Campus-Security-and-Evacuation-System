#include <Arduino.h>

// --- Configuration ---
const int MOTION_INPUT_PIN = 18;
const int RFID_INPUT_PIN = 19;
const long DEBUG_BAUD_RATE = 115200;
const char *FAKE_RFID_TAG = "FAKE123"; // Hardcoded tag

// --- State Machine Definition ---
enum StateMachineTest
{
    IDLE,
    ACTION
};
StateMachineTest currentState = IDLE;

// --- Flags & Data ---
bool motionDetected = false;
bool rfidDetected = false;
#define MAX_RFID_TAG_LENGTH 12 // Match main code if possible
char rfidTag[MAX_RFID_TAG_LENGTH + 1] = {0};

// --- Previous State Variables (for edge detection/debounce if needed) ---
int lastMotionState = LOW;
int lastRfidState = LOW;
// Add debounce variables if necessary later

void setup()
{
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    delay(2000);
    Serial.println("\n--- ESP32 GPIO State Machine Test ---");
    Serial.print("Monitoring Motion Pin: ");
    Serial.println(MOTION_INPUT_PIN);
    Serial.print("Monitoring RFID Pin: ");
    Serial.println(RFID_INPUT_PIN);
    Serial.println("(Pins configured as INPUT_PULLDOWN)");

    pinMode(MOTION_INPUT_PIN, INPUT_PULLDOWN);
    pinMode(RFID_INPUT_PIN, INPUT_PULLDOWN);

    lastMotionState = digitalRead(MOTION_INPUT_PIN);
    lastRfidState = digitalRead(RFID_INPUT_PIN);
    Serial.print("Initial Motion State: ");
    Serial.println(lastMotionState == HIGH ? "HIGH" : "LOW");
    Serial.print("Initial RFID State: ");
    Serial.println(lastRfidState == HIGH ? "HIGH" : "LOW");
    Serial.println("Starting in IDLE state.");
}

void loop()
{
    // --- Read Inputs --- (Basic Read - Add Debounce later if needed)
    int currentMotionState = digitalRead(MOTION_INPUT_PIN);
    int currentRfidState = digitalRead(RFID_INPUT_PIN);

    // --- Update Flags based on inputs (Simple level detection) ---
    if (currentMotionState == HIGH)
    {
        // Consider motion detected whenever the pin is HIGH
        // This avoids needing complex debouncing for this simple test
        motionDetected = true;
        // Optional: Print only on change
        if (currentMotionState != lastMotionState)
        {
            Serial.println("Motion Signal HIGH");
        }
    }

    if (currentRfidState == HIGH)
    {
        // Trigger RFID detection only once when the signal goes HIGH
        if (!rfidDetected)
        { // Check if flag isn't already set
            rfidDetected = true;
            strcpy(rfidTag, FAKE_RFID_TAG);
            Serial.println("-> RFID Signal HIGH detected, flag SET.");
        }
        // Optional: Print only on change
        if (currentRfidState != lastRfidState)
        {
            Serial.println("RFID Signal HIGH");
        }
    }
    else
    {
        // If RFID signal goes LOW, allow the flag to be set again next time
        // We might clear the flag here OR rely on the state machine to clear it
        // For now, let's just allow re-triggering when HIGH is seen again.
    }

    // Update last known states for change detection prints
    lastMotionState = currentMotionState;
    lastRfidState = currentRfidState;

    // --- Minimal State Machine Logic ---
    if (currentState == IDLE && motionDetected)
    {
        Serial.println(F("*** Motion detected! Moving to ACTION state. ***"));
        currentState = ACTION;
        motionDetected = false; // Clear the flag now that we've acted on it
    }
    else if (currentState == ACTION)
    {
        // Check for RFID data while in ACTION state
        if (rfidDetected)
        {
            Serial.print(F("*** RFID Tag Processed in ACTION state: ["));
            Serial.print(rfidTag); // Print the hardcoded tag
            Serial.println(F("] ***"));
            rfidDetected = false; // Clear flag after handling
            // Optional: Transition back to IDLE or another state here?
            // currentState = IDLE; // Example: Go back to IDLE after processing RFID
        }
    }

    // Small delay
    delay(50);
}