#include "serial_handler.h"
#include "../config.h"

// --- Internal Serial Port References ---
// These are set during setupSerialHandler() based on config.h
// We assume the same assignments as initially defined in main.cpp
// (MKR on Serial1, ESP32 on Serial2)
// If these need to change, the logic should ideally be updated
// in setupSerialHandler or managed via pointers set in setup.
HardwareSerial &mkrPort = Serial1;   // Reference to the serial port for MKR communication
HardwareSerial &esp32Port = Serial2; // Reference to the serial port for ESP32 communication
// --- End Internal Serial Port References ---

/**
 * @brief Initializes the serial handler.
 * Currently, this function only serves as a placeholder for potential
 * future initialization logic specific to the handler.
 * The actual Serial.begin() calls are handled in main setup().
 */
void setupSerialHandler()
{
    // No specific initialization needed here for now,
    // as Serial.begin() is handled in main.cpp setup.
    // This function exists for future expansion if needed.
    Serial.begin(SERIAL_BAUD_RATE);
    Serial.println(F("Serial Handler Initialized (references set)."));
}

/**
 * @brief Sends the motion detected character ('M') to the ESP32 port.
 */
void sendMotionDetected()
{
    esp32Port.write('M');
    Serial.println(F("[Serial TX->ESP32] Sent: M (Motion)"));
}

/**
 * @brief Sends the RFID detected command ('R') followed by the mock tag
 *        and a null terminator to the ESP32 port.
 */
void sendRfidDetected()
{
    esp32Port.write('R');
    esp32Port.print(MOCK_RFID_TAG);
    esp32Port.write('\0'); // Null terminator
    Serial.print(F("[Serial TX->ESP32] Sent: R"));
    Serial.print(MOCK_RFID_TAG);
    Serial.println(F(" (RFID)"));
}

/**
 * @brief Sends the emergency signal character ('E') to the MKR port.
 */
void sendEmergencySignal()
{
    mkrPort.write('E');
    Serial.println(F("[Serial TX->MKR] Sent: E (Emergency)"));
}

/**
 * @brief Checks the MKR serial port for an incoming unlock command ('U').
 * Reads only one byte if available.
 * @return True if 'U' was received, false otherwise.
 */
bool checkForUnlockCommand()
{
    if (mkrPort.available() > 0)
    {
        char receivedChar = mkrPort.read();
        Serial.print(F("[Serial RX<-MKR] Received: "));
        Serial.write(receivedChar);
        Serial.println();
        if (receivedChar == 'U')
        {
            Serial.println(F("  -> Unlock command recognized."));
            return true;
        }
    }
    return false;
}