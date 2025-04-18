#ifndef CONFIG_H
#define CONFIG_H

// === Pin Definitions ===
#define TRIGGER_PIN 5 // Input pin receiving signal from Arduino Mega (Pin 4)
#define SERVO_PIN 9   // Output pin connected to Servo motor signal line

// === Servo Parameters ===
#define SERVO_UNLOCK_ANGLE 95     // Angle in degrees for the unlocked position
#define SERVO_LOCK_ANGLE 180     // Angle in degrees for the locked position
#define SERVO_UNLOCK_HOLD_MS 10000 // Time (ms) to wait before re-locking after unlock trigger

// === Serial Configuration ===
#define DEBUG_SERIAL_BAUD 115200 // Baud rate for Serial debugging

#endif // CONFIG_H