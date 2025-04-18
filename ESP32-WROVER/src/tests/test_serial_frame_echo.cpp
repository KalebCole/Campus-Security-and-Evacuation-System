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
#define MAX_BUFFER_SIZE 64     // Match serial_handler.h
#define MAX_RFID_TAG_LENGTH 12 // Match serial_handler.h

// Command identifiers (match serial_handler.h)
#define CMD_MOTION 'M'
#define CMD_RFID 'R'
#define CMD_EMERGENCY 'E'

// --- Global Variables for Framing Logic ---
char serialBuffer[MAX_BUFFER_SIZE];
size_t bufferIndex = 0;
bool messageStarted = false;

// --- Global Variables for Parsed Data ---
bool motionDetected = false;
bool rfidDetected = false;
bool emergencyDetected = false;
char rfidTag[MAX_RFID_TAG_LENGTH + 1] = {0};

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
 * Parse a complete message (content received without start/end chars)
 * Sets appropriate flags based on the command character and data.
 * (Adapted from serial_handler.cpp)
 */
void parseSerialMessage(const char *message, size_t length)
{
    if (length < 1)
    {
        Serial.println(F("PARSER: Received empty message content."));
        return; // Empty message
    }

    char command = message[0];
    Serial.print(F("PARSER: Parsing content: "));
    Serial.println(message);

    switch (command)
    {
    case CMD_MOTION:
        motionDetected = true;
        Serial.println("PARSER:   -> Motion detected flag set.");
        break;

    case CMD_RFID:
        if (length > 1)
        {
            // Copy RFID data (excluding command character 'R')
            size_t tagLength = min(length - 1, (size_t)MAX_RFID_TAG_LENGTH);
            memcpy(rfidTag, message + 1, tagLength);
            rfidTag[tagLength] = '\0'; // Ensure null termination
            rfidDetected = true;
            Serial.print("PARSER:   -> RFID detected flag set. Tag: ");
            Serial.println(rfidTag);
        }
        else
        {
            Serial.println("PARSER:   -> RFID command received with no tag data.");
        }
        break;

    case CMD_EMERGENCY:
        emergencyDetected = true;
        Serial.println("PARSER:   -> Emergency detected flag set.");
        break;

    default:
        Serial.print("PARSER:   -> Unknown command received: ");
        Serial.println(command);
        break;
    }
}

/**
 * Clear all serial event flags
 * (Adapted from serial_handler.cpp)
 */
void clearSerialFlags()
{
    if (motionDetected || rfidDetected || emergencyDetected)
    {
        Serial.println(F("TEST: Clearing flags..."));
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
    Serial.println(F("\n--- ESP32 Frame Parser Test ---"));
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
    clearSerialFlags(); // Initialize flags to false
    memset(serialBuffer, 0, sizeof(serialBuffer));
}

void loop()
{
    while (MegaSerial.available() > 0)
    {
        // Read the incoming character
        char inChar = (char)MegaSerial.read();

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
                // End of the message found
                if (bufferIndex < MAX_BUFFER_SIZE - 1) // Check if buffer has space for '>' and null terminator
                {
                    serialBuffer[bufferIndex++] = '>'; // Store the end char
                    serialBuffer[bufferIndex] = '\0';  // Null-terminate the buffer
                    messageStarted = false;            // Reset message flag

                    // Print the complete frame
                    Serial.print(F("Received frame: "));
                    Serial.println(serialBuffer);

                    // Parse the received content
                    parseSerialMessage(serialBuffer + 1, bufferIndex - 2);
                }
                else
                {
                    // Buffer would overflow with '>', discard
                    Serial.println(F("Error: Buffer overflow on receiving '>'. Discarding."));
                    messageStarted = false;
                    bufferIndex = 0;
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

    // Clear flags periodically for testing multiple messages
    // You might adjust the timing or trigger condition later
    static unsigned long lastFlagClearTime = 0;
    if (millis() - lastFlagClearTime > 7000) // Clear flags ~7 seconds after last clear
    {
        clearSerialFlags();
        lastFlagClearTime = millis();
    }
}