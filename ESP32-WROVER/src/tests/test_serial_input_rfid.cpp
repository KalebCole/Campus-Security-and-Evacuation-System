// this will monitor the serial input from the mega and then print the input to the serial monitor
// we are going to send a fake rfid tag
// the esp32 will read the start character 'R' and then the rfid tag and then the null terminator '\0'
// the esp32 will then print the rfid tag to the serial monitor

#include <Arduino.h>

// --- Test Configuration ---
// Goal: Listen on Serial2 (Pins 12/13, 9600 Baud) for an RFID message from the Mega.
// Format: Start charealoadracter 'R', followed by the RFID tag string, ending with '\0'.
// Action: Print the received RFID tag to the main Serial Monitor.
// NEED TO VERIFY: IS THIS GOING TO SEND A CHARACTER AT A TIME OR A STRING?

// --- Constants ---
// Serial Port for Mega communication (Using Serial2 hardware UART)
HardwareSerial &MegaSerial = Serial2;
const int ESP32_TX_PIN = 18;      // Connect this to Mega RX (Pin 17)
const int ESP32_RX_PIN = 19;      // Connect this to Mega TX (Pin 16)
const long MEGA_BAUD_RATE = 9600; // MUST match ESP32_SERIAL_BAUD on Mega

// Serial Port for Debugging (USB Monitor)
const long DEBUG_BAUD_RATE = 115200;

// RFID Message Handling
const char START_CHAR = 'R';
const char END_CHAR = '\0';
const int RFID_BUFFER_SIZE = 32;           // Max tag length + 1 for null terminator
const unsigned long READ_TIMEOUT_MS = 100; // Timeout for receiving tag after 'R'

// --- Global Variables ---
char rfidBuffer[RFID_BUFFER_SIZE];
byte bufferIndex = 0;
enum ReceiveState
{
    WAITING_FOR_R,
    READING_TAG
};
ReceiveState currentState = WAITING_FOR_R;
unsigned long tagReadStartTime = 0;

void setup()
{
    Serial.begin(DEBUG_BAUD_RATE);
    while (!Serial)
        ;
    Serial.println(F("\n--- ESP32 RFID Receiver Test ---"));
    Serial.print(F("Listening for 'R'<tag>'\\0' message from Mega on Serial2 "));
    Serial.print(F("(RX="));
    Serial.print(ESP32_RX_PIN);
    Serial.print(F(", TX="));
    Serial.print(ESP32_TX_PIN);
    Serial.print(F(") at "));
    Serial.print(MEGA_BAUD_RATE);
    Serial.println(F(" baud..."));

    // Initialize Serial2 connection to Mega
    MegaSerial.begin(MEGA_BAUD_RATE, SERIAL_8N1, ESP32_RX_PIN, ESP32_TX_PIN);
}

void loop()
{       
    if (MegaSerial.available() > 0)
    {
        char receivedChar = MegaSerial.read();
        Serial.print(F("Received from Mega: "));
        Serial.write(receivedChar);
        Serial.println(F(""));
        switch (currentState)
        {
        case WAITING_FOR_R:
            if (receivedChar == START_CHAR)
            {
                bufferIndex = 0;                         // Reset buffer
                memset(rfidBuffer, 0, RFID_BUFFER_SIZE); // Clear buffer
                currentState = READING_TAG;
                tagReadStartTime = millis(); // Start timeout timer
                Serial.println(F("Received 'R', reading tag..."));
            }
            // Ignore other characters while waiting for 'R'
            break;

        case READING_TAG:
            // Check for timeout first
            if (millis() - tagReadStartTime > READ_TIMEOUT_MS)
            {
                Serial.println(F("Error: Timeout waiting for null terminator. Resetting."));
                currentState = WAITING_FOR_R;
                break; // Exit switch
            }

            if (receivedChar == END_CHAR)
            {
                // Message complete
                rfidBuffer[bufferIndex] = '\0'; // Ensure null termination (redundant but safe)
                Serial.print(F(">>> Received RFID Tag: ["));
                Serial.print(rfidBuffer);
                Serial.println(F("]"));
                currentState = WAITING_FOR_R; // Go back to waiting state
            }
            else
            {
                // Store character in buffer if space allows
                if (bufferIndex < RFID_BUFFER_SIZE - 1)
                {
                    rfidBuffer[bufferIndex++] = receivedChar;
                    // Reset timeout slightly on each valid character received (optional)
                    // tagReadStartTime = millis();
                }
                else
                {
                    // Buffer overflow
                    Serial.println(F("Error: Buffer overflow. Tag too long? Resetting."));
                    currentState = WAITING_FOR_R;
                }
            }
            break;
        }
    }

    // Check for timeout even if no character received this loop
    if (currentState == READING_TAG && (millis() - tagReadStartTime > READ_TIMEOUT_MS))
    {
        Serial.println(F("Error: Timeout waiting for null terminator (no new chars). Resetting."));
        currentState = WAITING_FOR_R;
    }
}
