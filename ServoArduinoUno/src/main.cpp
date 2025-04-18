#include <Arduino.h>
#include <Servo.h>
#include "config.h"

Servo doorServo; // Create servo object to control the door lock servo

// State machine for servo control
enum ServoState
{
  LOCKED,
  UNLOCKING
};
ServoState currentServoState = LOCKED;

unsigned long unlockStartTime = 0; // To track when the unlock sequence began
int lastTriggerState = LOW;        // Variable to store the previous trigger state for edge detection

void setup()
{
  Serial.begin(DEBUG_SERIAL_BAUD);
  Serial.println(F("\n--- Servo Arduino Uno Initializing ---"));

  // Configure trigger pin from Mega
  pinMode(TRIGGER_PIN, INPUT);
  Serial.print(F("Trigger Pin ("));
  Serial.print(TRIGGER_PIN);
  Serial.println(F(") configured as INPUT."));

  // Attach servo and set initial position
  doorServo.attach(SERVO_PIN);
  Serial.print(F("Servo attached to Pin "));
  Serial.println(SERVO_PIN);
  doorServo.write(SERVO_LOCK_ANGLE); // Start in the locked position
  currentServoState = LOCKED;
  Serial.print(F("Servo initialized to LOCKED position ("));
  Serial.print(SERVO_LOCK_ANGLE);
  Serial.println(F(" degrees)."));

  Serial.println(F("--- Setup Complete ---"));
}

void loop()
{
  // print what the pin is reading
  Serial.print(F("Trigger Pin ("));
  Serial.print(TRIGGER_PIN);
  Serial.print(F(") is reading: "));
  Serial.println(digitalRead(TRIGGER_PIN));
  delay(1000);
}
// void loop()
// {
//   // Read the state of the trigger pin from the Mega
//   int triggerState = digitalRead(TRIGGER_PIN);

//   // --- State Machine Logic ---

//   if (currentServoState == LOCKED)
//   {
//     // If we are LOCKED and receive a RISING EDGE (LOW to HIGH) signal, start unlocking
//     if (triggerState == HIGH && lastTriggerState == LOW)
//     {
//       Serial.println(F("Trigger received (Rising Edge). Unlocking..."));
//       doorServo.write(SERVO_UNLOCK_ANGLE);
//       unlockStartTime = millis();    // Record the time we started unlocking
//       currentServoState = UNLOCKING; // Change state
//       Serial.print(F("Servo moved to UNLOCK position ("));
//       Serial.print(SERVO_UNLOCK_ANGLE);
//       Serial.println(F(" degrees)."));
//     }
//   }
//   else if (currentServoState == UNLOCKING)
//   {
//     // If we are UNLOCKING, check if the hold time has passed
//     if (millis() - unlockStartTime >= SERVO_UNLOCK_HOLD_MS)
//     {
//       Serial.println(F("Unlock hold time finished. Locking..."));
//       doorServo.write(SERVO_LOCK_ANGLE);
//       currentServoState = LOCKED; // Change state back to locked
//       Serial.print(F("Servo moved to LOCKED position ("));
//       Serial.print(SERVO_LOCK_ANGLE);
//       Serial.println(F(" degrees)."));
//     }
//   }

//   // Store the current trigger state for the next loop iteration's edge detection
//   lastTriggerState = triggerState;

//   // No delay needed here as the logic is non-blocking
// }
