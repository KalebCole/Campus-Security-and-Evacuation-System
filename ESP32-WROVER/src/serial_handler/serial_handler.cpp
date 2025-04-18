#include "serial_handler.h"

// Define serial port
HardwareSerial &MegaSerial = Serial2;

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
 * @param c The character to check
 * @return true if the character is useful, false otherwise
 */
bool isUsefulChar(char c)
{
    return (c >= '0' && c <= '9') ||           // digits
           c == 'M' || c == 'R' || c == 'E' || // valid message types
           c == '<' || c == '>';               // delimiters
}
/**
 * Initialize the serial communication with Arduino Mega
 */
void setupSerialHandler()
{
    // Configure the RX pin with an internal pull-up resistor before beginning SerialPort
    pinMode(SERIAL_RX_PIN, INPUT_PULLUP);
    MegaSerial.begin(SERIAL_BAUD_RATE, SERIAL_8N1, SERIAL_RX_PIN, SERIAL_TX_PIN);
    Serial.print(F("Serial Handler initialized on UART1 (RX:"));
    Serial.print(SERIAL_RX_PIN);
    Serial.print(F(", TX:"));
    Serial.print(SERIAL_TX_PIN);
    Serial.print(F(") at "));
    Serial.print(SERIAL_BAUD_RATE);
    Serial.println(F(" baud."));
}

/**
 * Process any available serial data
 * Looks for messages framed by START_CHAR and END_CHAR
 */
void processSerialData()
{
    while (MegaSerial.available() > 0)
    {
        // Read the incoming character as char
        char inChar = (char)MegaSerial.read();

        // Only process characters deemed useful by the filter function
        if (isUsefulChar(inChar))
        {
            // Debug print for useful characters received
            Serial.print(F("Useful char received: "));
            Serial.println(inChar);

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
                    parseSerialMessage(serialBuffer, bufferIndex);
                }
                else
                {
                    Serial.println(F("Received empty <> message."));
                }
                // Reset buffer index for safety, although parse should handle content
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
}

/**
 * Parse a complete message (received without start/end chars)
 * Sets appropriate flags based on the command character and data.
 */
void parseSerialMessage(const char *message, size_t length)
{
    if (length < 1)
    {
        Serial.println(F("Received empty message."));
        return; // Empty message
    }

    char command = message[0];
    Serial.print(F("Parsing serial message: "));
    Serial.println(message);

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
            Serial.print("  -> RFID detected flag set. Tag: ");
            Serial.println(rfidTag);
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
 */
void clearSerialFlags()
{
    motionDetected = false;
    rfidDetected = false;
    emergencyDetected = false;
    memset(rfidTag, 0, sizeof(rfidTag)); // Clear the tag buffer
}
