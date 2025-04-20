#include <Arduino.h>

// --- Pin and Serial Configuration ---
// Match these with serial_handler.h and config.h
#define SERIAL_RX_PIN 19
#define SERIAL_TX_PIN 18
#define SERIAL_BAUD_RATE 9600

// Use Serial2 (UART1 typically on ESP32-WROVER for pins 18/19)
HardwareSerial &MegaSerial = Serial2;

// --- Message Protocol Constants ---
#define START_CHAR '<'
#define END_CHAR '>'
#define MAX_BUFFER_SIZE 64 // Match serial_handler.h

// --- Command Identifiers (from serial_handler.h) ---
#define CMD_MOTION 'M'
#define CMD_RFID 'R'
#define CMD_EMERGENCY 'E'

// --- Define the flag variables (similar to serial_handler) ---
bool motionDetected = false;
bool rfidDetected = false;
bool emergencyDetected = false;
#define MAX_RFID_TAG_LENGTH 12 // Ensure this matches MOCK_RFID_TAG length + buffer allowance
char rfidTag[MAX_RFID_TAG_LENGTH + 1] = {0};

// --- State Machine Definition (Minimal) ---
enum StateMachineTest
{
    IDLE,
    ACTION
};
StateMachineTest currentState = IDLE;

// --- Global Variables for Framing Logic ---
char serialBuffer[MAX_BUFFER_SIZE];
size_t bufferIndex = 0;
bool messageStarted = false;

// --- Debug Serial (USB Monitor) ---
const long DEBUG_BAUD_RATE = 115200;

/**
 * Check if a character is useful for the serial handler
 * (Copied from serial_handler.cpp)
 */
bool isUsefulChar(char c)
{
    return (c >= '0' && c <= '9') ||           // digits
           (c >= 'A' && c <= 'Z') ||           // Uppercase letters (for RFID tags)
           c == 'M' || c == 'R' || c == 'E' || // valid message types
           c == '<' || c == '>';               // delimiters
}

/**
 * Parse a complete message (received without start/end chars)
 * Sets appropriate flags based on the command character and data.
 * (Adapted from serial_handler.cpp)
 */
void parseSerialMessage(const char *message, size_t length)
{
    if (length < 1)
    {
        Serial.println(F("Received empty message content inside frame."));
        return; // Empty message
    }

    char command = message[0];
    Serial.print(F("Parsing message content: "));
    Serial.println(message);

    switch (command)
    {
    case CMD_MOTION:
        motionDetected = true;
        Serial.println("  -> Motion detected flag SET.");
        break;

    case CMD_RFID:
        if (length > 1)
        {
            // Copy RFID data (excluding command character 'R')
            size_t tagLength = min(length - 1, (size_t)MAX_RFID_TAG_LENGTH);
            memcpy(rfidTag, message + 1, tagLength);
            rfidTag[tagLength] = '\0'; // Ensure null termination
            rfidDetected = true;
            Serial.print("  -> RFID detected flag SET. Tag: [");
            Serial.print(rfidTag);
            Serial.println("]");
        }
        else
        {
            Serial.println("  -> RFID command received with no tag data.");
        }
        break;

    case CMD_EMERGENCY:
        emergencyDetected = true;
        Serial.println("  -> Emergency detected flag SET.");
        break;

    default:
        Serial.print("  -> Unknown command received in frame: ");
        Serial.println(command);
        break;
    }
}

/**
 * Clear all serial event flags
 */
void clearSerialFlags()
{
    // Only clear if any flag is actually set, to avoid spamming
    if (motionDetected || rfidDetected || emergencyDetected)
    {
        Serial.println(F("--- Clearing Serial Flags ---"));
        motionDetected = false;
        rfidDetected = false;
        emergencyDetected = false;
        memset(rfidTag, 0, sizeof(rfidTag)); // Clear the tag buffer
    }
}

void setup()
{
    // Start the USB Serial Monitor
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    Serial.println(F("\n--- ESP32 Frame Echo Test ---"));
    Serial.print(F("Listening on ESP32 Serial2 "));
    Serial.print(F("(RX="));
    Serial.print(SERIAL_RX_PIN);
    Serial.print(F(", TX="));
    Serial.print(SERIAL_TX_PIN);
    Serial.print(F(") at "));
    Serial.print(SERIAL_BAUD_RATE);
    Serial.println(F(" baud..."));
    Serial.println(F("Waiting for frames like <...>"));

    // Configure RX pin with pull-up (Important!)
    pinMode(SERIAL_RX_PIN, INPUT_PULLUP);

    // Start Serial2 connection to Mega
    MegaSerial.begin(SERIAL_BAUD_RATE, SERIAL_8N1, SERIAL_RX_PIN, SERIAL_TX_PIN);

    // Clear state variables
    bufferIndex = 0;
    messageStarted = false;
    memset(serialBuffer, 0, sizeof(serialBuffer));
}

void loop()
{
    // Add check for available count
    int availableCount = MegaSerial.available();
    // Read the incoming characters
    if (availableCount > 0)
    {
        Serial.printf("SerialPort.available() = %d entering while loop\n", availableCount);
    }
    // --- Process Incoming Serial Data ---
    while (MegaSerial.available() > 0)
    {
        char inChar = (char)MegaSerial.read();
        // print the amount of characters available
        Serial.print(F("Characters available: "));
        Serial.println(MegaSerial.available());
        // print the character
        Serial.print(F("Received character: "));
        Serial.println(inChar);

        // Filter out non-useful characters
        if (isUsefulChar(inChar))
        {
            // Uncomment for verbose debugging:
            // Serial.print(F("Useful char: ")); Serial.println(inChar);

            if (inChar == START_CHAR)
            {
                // Start of a potential message
                messageStarted = true;
                bufferIndex = 0;                 // Reset buffer for new message
                serialBuffer[bufferIndex] = '<'; // Store the start char
                bufferIndex++;
            }
            else if (inChar == END_CHAR && messageStarted)
            {
                /* --- Remove Diagnostic Prints ---
                // --- DIAGNOSTIC STEP ---
                // Store the end char and null-terminate temporarily for inspection
                if (bufferIndex < MAX_BUFFER_SIZE -1) {
                    serialBuffer[bufferIndex] = '>';
                    serialBuffer[bufferIndex + 1] = '\0';
                    Serial.println(F("--- DEBUG: Entering END_CHAR Block ---"));
                    Serial.print(F("DEBUG: bufferIndex before final store = ")); Serial.println(bufferIndex);
                    Serial.print(F("DEBUG: serialBuffer content = [")); Serial.print(serialBuffer); Serial.println(F("]"));
                } else {
                     Serial.println(F("--- DEBUG: Buffer overflow BEFORE storing final '>' ---"));
                     messageStarted = false;
                     bufferIndex = 0;
                     continue; // Skip further processing in this block
                }
                 // --- END DIAGNOSTIC STEP ---
                messageStarted = false; // Reset message flag early for diagnostic
                */

                // --- Re-enable Parsing Logic ---
                messageStarted = false; // Reset message flag

                // End of the message found
                if (bufferIndex < MAX_BUFFER_SIZE - 1) // Check if buffer has space for '>' and null terminator
                {
                    // Store the end char and null-terminate
                    serialBuffer[bufferIndex++] = '>';
                    serialBuffer[bufferIndex] = '\0';
                    // messageStarted = false; // Already did this above

                    // Print the complete frame
                    Serial.print(F("Received frame: "));
                    Serial.println(serialBuffer);

                    // Extract content: Skip first char '<', length is bufferIndex after storing null
                    // The actual content length is bufferIndex - 2 (excluding < and >)
                    if (bufferIndex >= 3)
                    { // Check if buffer holds at least <x>
                        char contentBuffer[MAX_BUFFER_SIZE];
                        size_t contentLength = bufferIndex - 2;                  // Correct length of content between <>
                        strncpy(contentBuffer, serialBuffer + 1, contentLength); // Copy content
                        contentBuffer[contentLength] = '\0';                     // Null terminate the content correctly
                        parseSerialMessage(contentBuffer, contentLength);
                    }
                    else
                    {
                        Serial.println(F("Received empty <> frame content."));
                    }
                }
                else if (bufferIndex == 1) // Only received '<'
                {
                    Serial.println(F("Error: Received only '<' before '>'. Discarding."));
                }
                else // Buffer overflow occurred before receiving '>' or other error
                {
                    Serial.println(F("Error: Invalid frame state on receiving '>'. Discarding."));
                }

                // Reset buffer index after processing or error
                bufferIndex = 0;
            }
            else if (messageStarted)
            {
                // We are inside a message, store the character if buffer has space
                if (bufferIndex < MAX_BUFFER_SIZE - 1)
                {
                    serialBuffer[bufferIndex++] = inChar;
                }
                else
                {
                    // Buffer overflow - discard message and reset
                    Serial.println(F("Error: Serial buffer overflow! Discarding message."));
                    messageStarted = false;
                    bufferIndex = 0;
                }
            }
            // else: Character is useful but received outside a message (e.g., '>' without '<'), ignore it.
        }
        // else: Character was not useful (noise), discard it automatically.
    }

    // --- Emergency Check (Top Level) ---
    // This check happens regardless of the current IDLE/ACTION state
    if (emergencyDetected)
    {
        Serial.println(F("!!! EMERGENCY DETECTED !!!"));
        emergencyDetected = false; // Clear flag after handling
    }

    // --- Minimal State Machine Logic ---
    if (currentState == IDLE && motionDetected)
    {
        Serial.println(F("*** Motion detected! Moving to ACTION state. ***"));
        currentState = ACTION;
        motionDetected = false; // Clear the flag now that we've acted on it
        // Note: rfidDetected and emergencyDetected flags remain until explicitly cleared or acted upon
    }
    else if (currentState == ACTION)
    {
        // Check for RFID data while in ACTION state
        if (rfidDetected)
        {
            Serial.print(F("*** RFID Tag Processed in ACTION state: ["));
            Serial.print(rfidTag);
            Serial.println(F("] ***"));
            rfidDetected = false; // Clear flag after handling
            // We could potentially transition back to IDLE or another state here
            // For this test, we'll just stay in ACTION
        }
    }
}