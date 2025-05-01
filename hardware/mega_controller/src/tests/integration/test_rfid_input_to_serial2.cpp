// Test: Send all framed commands (<M>, <R[tag]>, <E>) sequentially to ESP32 via Serial2.

#include "../../config.h"
#include <Arduino.h>

// --- Test Configuration ---
// Goal: Send <M>, then <R[MOCK_RFID_TAG]>, then <E> via Serial2.
// Method: Automatic sequence with delays in the loop.

// --- Constants ---
const unsigned long SEND_DELAY_MS = 5000; // Delay between sending messages (ms)

// --- Global Variables ---
enum SendState
{
    SEND_M,
    WAIT_1,
    SEND_R,
    WAIT_2,
    SEND_E,
    DONE
};
SendState currentState = SEND_M;
unsigned long lastSendTime = 0;

void setup()
{
    Serial.begin(DEBUG_SERIAL_BAUD);
    while (!Serial)
        ;
    Serial.println(F("\n--- Test: Send All Framed Commands Sequentially --- "));

    // Initialize Serial2 for ESP32 communication
    Serial2.begin(ESP32_SERIAL_BAUD);
    Serial.print(F("Serial2 (ESP32) initialized at "));
    Serial.print(ESP32_SERIAL_BAUD);
    Serial.println(F(" baud."));

    Serial.println(F("Starting send sequence..."));
    currentState = SEND_M;
    lastSendTime = millis(); // Initialize timer for first delay
}

void loop()
{
    unsigned long currentTime = millis();

    // Check if enough time has passed for the next action
    if (currentState != DONE && (currentTime - lastSendTime >= SEND_DELAY_MS))
    {

        switch (currentState)
        {
        case SEND_M:
            Serial.println(F("Sending <M>..."));
            Serial2.print("<M>");
            currentState = WAIT_1;
            break;
        case WAIT_1: // Wait period after sending M
            currentState = SEND_R;
            break;
        case SEND_R: // Send RFID signal
            Serial.println(F("Sending <R" MOCK_RFID_TAG ">..."));
            Serial2.print("<R");
            Serial2.print(MOCK_RFID_TAG);
            Serial2.print(">");
            currentState = WAIT_2;
            break;
        case WAIT_2: // Wait period after sending R
            currentState = SEND_E;
            break;
        case SEND_E: // Send Emergency signal
            Serial.println(F("Sending <E>..."));
            Serial2.print("<E>");
            currentState = DONE;
            Serial.println(F("--- Send Sequence Complete --- "));
            break;

        case DONE:
            // Should not reach here due to outer check
            break;
        }
        lastSendTime = currentTime; // Reset timer for the next delay/action
    }

    // Once DONE, the loop does nothing further.
}