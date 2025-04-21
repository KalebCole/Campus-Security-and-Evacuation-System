#include <Arduino.h>
#include "../../config.h" // Include main config from parent src directory

// Test: Send 'E' character over Serial2 (to ESP32) when prompted via Serial Monitor.
HardwareSerial &MegaSerial = Serial2;

void setup()
{
    // Initialize Debug Serial (Serial Monitor via USB)
    Serial.begin(DEBUG_SERIAL_BAUD);
    while (!Serial)
        ;
    Serial.println(F("\n--- Test: Send 'E' via MegaSerial (ESP32) ---"));

    // Initialize MegaSerial for ESP32 communication
    MegaSerial.begin(ESP32_SERIAL_BAUD);
    Serial.print(F("MegaSerial initialized at "));
    Serial.print(ESP32_SERIAL_BAUD);
    Serial.println(F(" baud."));

    Serial.println(F("Enter 'e' to send 'E' character to ESP32 via MegaSerial."));
    Serial.println(F("Enter 'm' to send 'M' character to ESP32 via MegaSerial."));
    Serial.println(F("Enter 'r' to send 'R' character to ESP32 via MegaSerial."));
}

void loop()
{
    if (Serial.available() > 0)
    {
        char command = Serial.read();

        if (command == 'e')
        {
            Serial.print(F("Sending Framed '<E>' via MegaSerial (Pin "));
            Serial.print(ESP32_SERIAL_TX_PIN); // TX Pin for MegaSerial
            Serial.println(F(")..."));

            // Send framed message
            MegaSerial.print("<E>");

            Serial.println(F("'<E>' sent."));
        }
        else if (command == 'm')
        {
            Serial.print(F("Sending '<M>' via MegaSerial (Pin "));
            Serial.print(ESP32_SERIAL_TX_PIN); // TX Pin for MegaSerial
            Serial.println(F(")..."));

            MegaSerial.print("<M>");
        }
        else if (command == 'r')
        {
            Serial.print(F("Sending '<R' via MegaSerial (Pin "));
            Serial.print(ESP32_SERIAL_TX_PIN); // TX Pin for MegaSerial
            Serial.println(F(")..."));

            MegaSerial.print("<R");
            MegaSerial.print(MOCK_RFID_TAG);
            MegaSerial.print(">");
        }
        else
        {
            Serial.print(F("Unknown command: "));
            Serial.write(command);
            Serial.println();
            Serial.println(F("Enter 'e' to send '<E>' character to ESP32 via MegaSerial."));
        }
    }
}