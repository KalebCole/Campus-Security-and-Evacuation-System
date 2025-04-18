// this is a test to see if the pins are working

#include "../../config.h"
#include <Arduino.h>

void setup()
{
    Serial.begin(DEBUG_SERIAL_BAUD);
    Serial.println(F("Testing Pins"));
    pinMode(4, OUTPUT);
    pinMode(5, INPUT);
    pinMode(6, INPUT);
    pinMode(7, INPUT);
}

void loop()
{
    // testing 4-7 on the mega
    Serial.println(F("Testing pins 4-7"));
    Serial.print(F("Pin 4: "));
    Serial.println(digitalRead(4));
    Serial.println(F("+++++=========+++++"));

    Serial.print(F("Pin 5: "));
    Serial.println(digitalRead(5));
    Serial.println(F("+++++=========+++++"));

    Serial.print(F("Pin 6: "));
    Serial.println(digitalRead(6));
    Serial.println(F("+++++=========+++++"));

    Serial.print(F("Pin 7: "));
    Serial.println(digitalRead(7));
    Serial.println(F("+++++=========+++++"));
    delay(1000);
    // TODO: Might need to remvoe the delay
} 