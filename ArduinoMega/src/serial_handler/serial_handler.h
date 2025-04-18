#ifndef SERIAL_HANDLER_H
#define SERIAL_HANDLER_H

#include <Arduino.h>
#include "../config.h" // Include main config

// Initializes the serial handler with the designated ports
// Should be called once in setup()
void setupSerialHandler();

// Sends the motion detected signal ('M') to the ESP32
void sendMotionDetected();

// Sends the RFID detected signal ('R' + tag) to the ESP32
void sendRfidDetected();

// Sends the emergency signal ('E') to the MKR WiFi 1010
void sendEmergencySignal();

// Checks the MKR serial port for an unlock command ('U')
// Returns true if 'U' is received, false otherwise
bool checkForUnlockCommand();

#endif // SERIAL_HANDLER_H