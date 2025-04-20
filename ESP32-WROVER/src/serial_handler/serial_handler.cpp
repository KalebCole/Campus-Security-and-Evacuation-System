#include "serial_handler.h"

// Define serial port
// Use Serial2 (UART1 typically on ESP32-WROVER for pins 18/19)
// NOTE: Ensure config.h defines SERIAL_RX_PIN=19, SERIAL_TX_PIN=18
HardwareSerial &SerialPort = Serial2; // Renamed from MegaSerial to SerialPort for consistency

// Define the flag variables (defined here, declared extern in .h)
bool motionDetected = false;
bool rfidDetected = false;
bool emergencyDetected = false;
char rfidTag[MAX_RFID_TAG_LENGTH + 1] = {0};

// Buffer for receiving data
char serialBuffer[MAX_BUFFER_SIZE];
size_t bufferIndex = 0;
bool messageStarted = false;

/**
 * Check if a character is useful for the serial handler
 * (Updated based on test_serial_frame_echo.cpp)
 */
bool isUsefulChar(char c)
{
    return (c >= '0' && c <= '9') ||           // digits
           (c >= 'A' && c <= 'Z') ||           // Uppercase letters (for RFID tags)
           c == 'M' || c == 'R' || c == 'E' || // valid message types
           c == '<' || c == '>';               // delimiters
}

/**
 * Initialize the serial communication with Arduino Mega
 */
void setupSerialHandler()
{
    // Configure the RX pin with an internal pull-up resistor before beginning SerialPort
    pinMode(SERIAL_RX_PIN, INPUT_PULLUP); // Ensure INPUT_PULLUP
    SerialPort.begin(SERIAL_BAUD_RATE, SERIAL_8N1, SERIAL_RX_PIN, SERIAL_TX_PIN);
    Serial.print(F("Serial Handler initialized on UART1 (RX:"));
    Serial.print(SERIAL_RX_PIN);
    Serial.print(F(", TX:"));
    Serial.print(SERIAL_TX_PIN);
    Serial.print(F(") at "));
    Serial.print(SERIAL_BAUD_RATE);
    Serial.println(F(" baud."));

    // Clear state variables at init
    bufferIndex = 0;
    messageStarted = false;
    memset(serialBuffer, 0, sizeof(serialBuffer));
    clearSerialFlags(); // Clear flags on setup
}

/**
 * Process any available serial data
 * Looks for messages framed by START_CHAR and END_CHAR
 * (Logic ported from test_serial_frame_echo.cpp)
 */
void processSerialData()
{
    // Add check for available count
    int availableCount = SerialPort.available();
    if (availableCount > 0)
    {
        Serial.printf("SerialPort.available() = %d entering while loop\n", availableCount);
    }

    while (SerialPort.available() > 0) // Use SerialPort object
    {
        // Read the incoming character as char
        char inChar = (char)SerialPort.read();
        Serial.printf("inChar = %c\n", inChar);

        // Only process characters deemed useful by the filter function
        if (isUsefulChar(inChar))
        {
            // Debug print for useful characters received (optional)
            // Serial.print(F("Useful char received: "));
            // Serial.println(inChar);

            if (inChar == START_CHAR)
            {
                // Start of a potential message
                messageStarted = true;
                bufferIndex = 0; // Reset buffer for new message
                // Don't store the start character itself
            }
            else if (inChar == END_CHAR && messageStarted)
            {
                // End of the message found
                serialBuffer[bufferIndex] = '\0'; // Null-terminate the buffer
                messageStarted = false;           // Reset message flag

                if (bufferIndex > 0) // Check if we actually got content between < >
                {
                    // Content is already in serialBuffer, null-terminated
                    parseSerialMessage(serialBuffer, bufferIndex);
                }
                else
                {
                    Serial.println(F("Received empty <> message."));
                }
                // Reset buffer index for safety
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
                    Serial.println(F("Serial buffer overflow! Discarding message."));
                    messageStarted = false;
                    bufferIndex = 0;
                }
            }
            // else: Character is useful but received outside a message (e.g., '>' without '<'), ignore it.
        }
        // else: Character was not useful (noise), discard it automatically.
    }
    // Correct location for exit message (optional)
    // Serial.println("Exiting processSerialData function (finished checking available)");
}

/**
 * Parse a complete message (received without start/end chars)
 * Sets appropriate flags based on the command character and data.
 * (Logic ported from test_serial_frame_echo.cpp)
 */
void parseSerialMessage(const char *message, size_t length)
{
    if (length < 1)
    {
        Serial.println(F("Received empty message content."));
        return; // Empty message
    }

    char command = message[0];
    // Optional: Print the raw message being parsed for debug
    // Serial.print(F("Parsing message content: ")); Serial.println(message);

    switch (command)
    {
    case CMD_MOTION:
        motionDetected = true;
        Serial.println("  -> Motion detected flag set.");
        break;

    case CMD_RFID:
        if (length > 1)
        {
            // Copy RFID data (excluding command character 'R')
            size_t tagLength = min(length - 1, (size_t)MAX_RFID_TAG_LENGTH);
            memcpy(rfidTag, message + 1, tagLength);
            rfidTag[tagLength] = '\0'; // Ensure null termination
            rfidDetected = true;
            Serial.print("  -> RFID detected flag set. Tag: [");
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
        Serial.println("  -> Emergency detected flag set.");
        break;

    default:
        Serial.print("  -> Unknown command received: ");
        Serial.println(command);
        break;
    }
}

/**
 * Clear all serial event flags
 * (Logic ported from test_serial_frame_echo.cpp)
 */
void clearSerialFlags()
{
    // Optional: Add print statement if needed
    // if (motionDetected || rfidDetected || emergencyDetected) {
    //     Serial.println(F("--- Clearing Serial Flags ---"));
    // }
    motionDetected = false;
    rfidDetected = false;
    emergencyDetected = false;
    memset(rfidTag, 0, sizeof(rfidTag)); // Clear the tag buffer
}
