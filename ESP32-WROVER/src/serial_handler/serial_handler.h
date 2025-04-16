#ifndef SERIAL_HANDLER_H
#define SERIAL_HANDLER_H

#include <Arduino.h>

// Serial communication pins
#define SERIAL_RX_PIN 7
#define SERIAL_TX_PIN 6
#define SERIAL_BAUD_RATE 9600

// Message protocol constants
#define START_CHAR '<'
#define END_CHAR '>'
#define MAX_BUFFER_SIZE 64
#define MAX_RFID_TAG_LENGTH 12

// Command identifiers
#define CMD_MOTION 'M'
#define CMD_RFID 'R'
#define CMD_EMERGENCY 'E'

// Flag variables - declared as extern to be defined in the .cpp file
extern bool motionDetected;
extern bool rfidDetected;
extern bool emergencyDetected;
extern char rfidTag[MAX_RFID_TAG_LENGTH + 1]; // +1 for null termination

// Function declarations
void setupSerialHandler();
void processSerialData();
void parseSerialMessage(const char *message, size_t length);
void clearSerialFlags();

#endif // SERIAL_HANDLER_H
