// reads from the emergency button pin

#include "../../config.h"
#include <Arduino.h>

void setup()
{
    Serial.begin(DEBUG_SERIAL_BAUD);
    Serial.println(("Emergency Input Test"));
    pinMode(EMERGENCY_PIN, INPUT);
}

void loop()
{
    int currentReading = digitalRead(EMERGENCY_PIN);
    Serial.print(F("Emergency Pin State: "));
    Serial.println(currentReading);
    delay(100);
}