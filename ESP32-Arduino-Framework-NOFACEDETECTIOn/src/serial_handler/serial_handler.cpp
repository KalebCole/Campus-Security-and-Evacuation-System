#include "serial_handler.h"

// Define serial port
HardwareSerial SerialPort(1); // Use UART1 for external communication

// Define the flag variables
bool motionDetected = false;
bool rfidDetected = false;
bool emergencyDetected = false;
char rfidTag[MAX_RFID_TAG_LENGTH + 1] = {0}; // Initialize with zeros

// Buffer for receiving data
char serialBuffer[MAX_BUFFER_SIZE];
size_t bufferIndex = 0;
bool messageStarted = false;

/**
 * Initialize the serial communication with Arduino Mega
 */
void setupSerialHandler()
{
    // Begin serial communication on UART1
    SerialPort.begin(SERIAL_BAUD_RATE, SERIAL_8N1, SERIAL_RX_PIN, SERIAL_TX_PIN);
    Serial.println("Serial handler initialized");
}

/**
 * Process any available serial data
 * Should be called regularly in the main loop
 */
void processSerialData()
{
    while (SerialPort.available() > 0)
    {
        char inChar = (char)SerialPort.read();

        // Check for message start
        if (inChar == START_CHAR)
        {
            messageStarted = true;
            bufferIndex = 0;
            continue; // Skip storing the start character
        }

        // Check for message end
        if (inChar == END_CHAR && messageStarted)
        {
            messageStarted = false;

            // Null terminate the message
            serialBuffer[bufferIndex] = '\0';

            // Process the complete message
            parseSerialMessage(serialBuffer, bufferIndex);

            // Reset buffer index
            bufferIndex = 0;
            continue; // Skip storing the end character
        }

        // Store character in buffer if within message bounds
        if (messageStarted && bufferIndex < MAX_BUFFER_SIZE - 1)
        {
            serialBuffer[bufferIndex++] = inChar;
        }
    }
}

/**
 * Parse a complete message and set appropriate flags
 * Returns true if message was valid and parsed successfully
 */
void parseSerialMessage(const char *message, size_t length)
{
    if (length < 1)
    {
        return; // Empty message
    }

    char command = message[0];

    switch (command)
    {
    case CMD_MOTION:
        motionDetected = true;
        Serial.println("Motion detected");
        break;

    case CMD_RFID:
        if (length > 1)
        {
            // Copy RFID data (excluding command character)
            size_t tagLength = min(length - 1, (size_t)MAX_RFID_TAG_LENGTH);
            memcpy(rfidTag, message + 1, tagLength);
            rfidTag[tagLength] = '\0'; // Ensure null termination
            rfidDetected = true;
            Serial.print("RFID detected: ");
            Serial.println(rfidTag);
        }
        break;

    case CMD_EMERGENCY:
        emergencyDetected = true;
        Serial.println("Emergency detected");
        break;

    default:
        Serial.print("Unknown command: ");
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
    memset(rfidTag, 0, sizeof(rfidTag));
}
