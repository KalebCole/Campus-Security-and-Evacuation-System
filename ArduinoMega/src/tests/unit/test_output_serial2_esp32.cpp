#include <Arduino.h>
#include "../../config.h" // Include main config from parent src directory

// Test: Send 'E' character over Serial2 (to ESP32) when prompted via Serial Monitor.

void setup()
{
    // Initialize Debug Serial (Serial Monitor via USB)
    Serial.begin(DEBUG_SERIAL_BAUD);
    while (!Serial)
        ;
    Serial.println(F("\n--- Test: Send 'E' via Serial2 (ESP32) ---"));

    // Initialize Serial2 for ESP32 communication
    Serial2.begin(ESP32_SERIAL_BAUD);
    Serial.print(F("Serial2 initialized at "));
    Serial.print(ESP32_SERIAL_BAUD);
    Serial.println(F(" baud."));

    Serial.println(F("Enter 'e' to send 'E' character to ESP32 via Serial2."));
    Serial.println(F("Enter 'm' to send 'M' character to ESP32 via Serial2."));
    Serial.println(F("Enter 'r' to send 'R' character to ESP32 via Serial2."));
}

void loop()
{
    if (Serial.available() > 0)
    {
        char command = Serial.read();

        if (command == 'e')
        {
            Serial.print(F("Sending Framed '<E>' via Serial2 (Pin "));
            Serial.print(ESP32_SERIAL_TX_PIN); // TX Pin for Serial2
            Serial.println(F(")..."));

            // Send framed message
            Serial2.print("<E>");

            Serial.println(F("'<E>' sent."));
        }
        else if (command == 'm')
        {
            Serial.print(F("Sending '<M>' via Serial2 (Pin "));
            Serial.print(ESP32_SERIAL_TX_PIN); // TX Pin for Serial2
            Serial.println(F(")..."));

            Serial2.print("<M>");
        }
        else if (command == 'r')
        {
            Serial.print(F("Sending '<R' via Serial2 (Pin "));
            Serial.print(ESP32_SERIAL_TX_PIN); // TX Pin for Serial2
            Serial.println(F(")..."));

            Serial2.print("<R");
            Serial2.print(MOCK_RFID_TAG);
            Serial2.print(">");
        }
        else
        {
            Serial.print(F("Unknown command: "));
            Serial.write(command);
            Serial.println();
            Serial.println(F("Enter 'e' to send '<E>' character to ESP32 via Serial2."));
        }
    }
}