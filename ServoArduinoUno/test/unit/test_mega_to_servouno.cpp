#include <Servo.h>

// --- Constants ---
const int TRIGGER_PIN = 5;
const int SERVO_PIN = 9;
const int SERVO_LOCK_ANGLE = 180;
const int SERVO_UNLOCK_ANGLE = 95;
const unsigned long DEBUG_SERIAL_BAUD = 115200;

const int BAD_STATE_LIMIT = 5;        // Number of consecutive LOW reads before locking
const unsigned long CHECK_INTERVAL = 100; // ms between checks

// --- Servo and State ---
Servo doorServo;

enum ServoState {
  LOCKED,
  UNLOCKED
};

ServoState currentServoState = LOCKED;
int lowCounter = 0;
int lastTriggerState = LOW;
unsigned long lastCheckTime = 0;

void setup() {
  Serial.begin(DEBUG_SERIAL_BAUD);
  delay(5000);
  Serial.println(F("\n--- Servo Arduino Uno Initializing ---"));

  pinMode(TRIGGER_PIN, INPUT);
  Serial.print(F("Trigger Pin ("));
  Serial.print(TRIGGER_PIN);
  Serial.println(F(") configured as INPUT."));

  doorServo.attach(SERVO_PIN);
  doorServo.write(SERVO_LOCK_ANGLE);
  currentServoState = LOCKED;
  Serial.print(F("Servo attached to Pin "));
  Serial.print(SERVO_PIN);
  Serial.println(F(" and initialized to LOCKED position."));

  Serial.println(F("--- Setup Complete ---"));
}

void loop() {
  unsigned long currentTime = millis();
  if (currentTime - lastCheckTime >= CHECK_INTERVAL) {
    lastCheckTime = currentTime;

    int triggerState = digitalRead(TRIGGER_PIN);
    
    
    // Unlocking trigger
    if (currentServoState == LOCKED && triggerState == HIGH) {
      Serial.println(F("Trigger HIGH detected. Unlocking..."));
      for (int i = SERVO_LOCK_ANGLE; i >= SERVO_UNLOCK_ANGLE; i--) {
        doorServo.write(i);
        delay(10);
      }
      currentServoState = UNLOCKED;
      lowCounter = 0;
      Serial.println(F("Servo is now UNLOCKED."));
    }

    // While UNLOCKED, monitor bad (LOW) states
    else if (currentServoState == UNLOCKED) {
      if (triggerState == LOW) {
        lowCounter++;
        Serial.print(F("Bad state detected. Counter: "));
        Serial.println(lowCounter);
        if (lowCounter >= BAD_STATE_LIMIT) {
          Serial.println(F("Bad state limit reached. Locking..."));
          for (int i = SERVO_UNLOCK_ANGLE; i <= SERVO_LOCK_ANGLE; i++) {
            doorServo.write(i);
            delay(10);
          }
          currentServoState = LOCKED;
          lowCounter = 0;
          Serial.println(F("Servo is now LOCKED."));
        }
      } else {
        // Reset counter if signal goes HIGH again
        if (triggerState == HIGH) {
          Serial.println(F("High signal recieved. Resetting low signal counter."));
        }
        lowCounter = 0;
      }
    }

    lastTriggerState = triggerState;
  }
}