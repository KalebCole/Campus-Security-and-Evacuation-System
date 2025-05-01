// GOAL

#include <Arduino.h>
#include "../src/serial_handler/serial_handler.h" // Include the header with extern declarations
#include "../src/config.h"

// --- Test Configuration ---
// Goal: Simulate receiving Motion ('M') then RFID ('R'+tag) from Mega
//       and verify that the corresponding extern flags and rfidTag buffer
//       are correctly updated by processSerialData().

const char *test_rfid_tag = "TEST123ABC";
unsigned long last_check_time = 0;
enum TestState
{
    START,
    SEND_M,
    WAIT_M,
    SEND_R,
    WAIT_R,
    DONE
};
TestState currentTestState = START;

void simulateSerialSend(const char *framed_msg)
{
    // Framed message should be like "<M>" or "<Rtag>"
    if (strlen(framed_msg) < 3 || framed_msg[0] != START_CHAR || framed_msg[strlen(framed_msg) - 1] != END_CHAR)
    {
        Serial.println(F("ERROR: Invalid framed message format for simulateSerialSend"));
        return;
    }
    Serial.print("Simulating reception of framed message: ");
    Serial.println(framed_msg);

    // Extract content between < and >
    size_t content_len = strlen(framed_msg) - 2;
    char content[MAX_BUFFER_SIZE];
    if (content_len < MAX_BUFFER_SIZE)
    {
        strncpy(content, framed_msg + 1, content_len);
        content[content_len] = '\0';
        // Directly call parseSerialMessage with the *inner* content
        parseSerialMessage(content, content_len);
    }
    else
    {
        Serial.println(F("ERROR: Simulated message content too long for buffer"));
    }
}

void setup()
{
    Serial.begin(115200);
    while (!Serial)
        ;
    Serial.println("\n--- Test: Serial Input RFID to Session Flags --- (Framed Protocol)");

    // Setup the serial handler (initializes pins/baud but not strictly needed for parsing test)
    // setupSerialHandler(); // We will call parseSerialMessage directly via simulateSerialSend

    Serial.println("Starting test sequence...");
    currentTestState = START;
    last_check_time = millis();
    clearSerialFlags(); // Ensure flags start clear
}

void loop()
{
    // We don't call processSerialData() directly here because we are manually
    // calling parseSerialMessage via simulateSerialSend to control the test sequence.

    unsigned long current_time = millis();

    if (current_time - last_check_time > 2000)
    { // Check every 2 seconds
        switch (currentTestState)
        {
        case START:
            Serial.println("--- Step 1: Sending Framed Motion Command (<M>) ---");
            simulateSerialSend("<M>");
            currentTestState = WAIT_M;
            break;

        case WAIT_M:
            Serial.print("Checking motionDetected flag: ");
            Serial.println(motionDetected ? "TRUE" : "FALSE");
            if (motionDetected)
            {
                Serial.println("Motion Detected Flag correctly set.");
                Serial.println("--- Step 2: Sending Framed RFID Command (<Rtag>) ---");
                // Construct <R + tag + > message
                char rfid_frame_msg[3 + MAX_RFID_TAG_LENGTH + 1]; // < R tag > \0
                snprintf(rfid_frame_msg, sizeof(rfid_frame_msg), "<%c%s>", CMD_RFID, test_rfid_tag);

                simulateSerialSend(rfid_frame_msg);
                currentTestState = WAIT_R;
            }
            else
            {
                Serial.println("ERROR: motionDetected flag not set!");
                currentTestState = DONE; // End test on error
            }
            break;

        case WAIT_R:
            Serial.print("Checking rfidDetected flag: ");
            Serial.println(rfidDetected ? "TRUE" : "FALSE");
            Serial.print("Checking rfidTag content: [");
            Serial.print(rfidTag);
            Serial.println("]");
            if (rfidDetected && strcmp(rfidTag, test_rfid_tag) == 0)
            {
                Serial.println("RFID Detected Flag and Tag Content correct.");
                Serial.println("--- Test Sequence Complete --- ");
                currentTestState = DONE;
            }
            else
            {
                Serial.println("ERROR: rfidDetected flag or tag content incorrect!");
                currentTestState = DONE; // End test on error
            }
            break;

        case DONE:
            // Do nothing, test finished
            break;
        }
        last_check_time = current_time;
    }

    if (currentTestState == DONE)
    {
        // Optional: hang here or perform cleanup
        delay(10000); // Long delay to stop further output
    }
}
