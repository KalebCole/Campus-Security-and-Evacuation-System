// this is a test to see if the emergency signal from the mega to the servo uno is working

// Read Emergency Pin (Pin 7): If HIGH, set Servo Trigger Output Pin (Pin 4) HIGH.
// If Emergency Pin is LOW, set Servo Trigger Output Pin LOW.
#include "../../config.h"
#include <Arduino.h>

void setup()
{
    Serial.begin(DEBUG_SERIAL_BAUD);
    Serial.println(F("--- Integration Test: Emergency Input (Pin 7) to Servo Trigger Output (Pin 4) ---"));
    pinMode(EMERGENCY_PIN, INPUT);
    pinMode(SERVO_TRIGGER_OUT_PIN, OUTPUT);

    // Initialize output pin to LOW
    digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
    Serial.print(F("Emergency Input Pin: "));
    Serial.println(EMERGENCY_PIN);
    Serial.print(F("Servo Trigger Output Pin: "));
    Serial.println(SERVO_TRIGGER_OUT_PIN);
    Serial.println(F("Monitoring Emergency Pin..."));
}

void loop()
{
    int emergencyState = digitalRead(EMERGENCY_PIN);

    // Print the state for debugging
    Serial.print(F("Emergency Pin State: "));
    Serial.print(emergencyState);

    if (emergencyState == HIGH)
    {
        // If Emergency Pin is HIGH, set Servo Trigger Pin HIGH
        digitalWrite(SERVO_TRIGGER_OUT_PIN, HIGH);
        Serial.println(F(" -> Setting Servo Trigger Pin HIGH"));
    }
    else
    {
        // If Emergency Pin is LOW, set Servo Trigger Pin LOW
        digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
        Serial.println(F(" -> Setting Servo Trigger Pin LOW"));
    }

    delay(100); // Check state periodically
}