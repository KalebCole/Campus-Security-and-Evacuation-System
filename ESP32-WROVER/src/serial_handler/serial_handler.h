#ifndef SERIAL_HANDLER_H
#define SERIAL_HANDLER_H

#include <Arduino.h>
#include "../config.h" // Include main config

// Serial communication pins (Corrected based on user input)
#define SERIAL_RX_PIN 19      // Connected to Mega TX Pin 16
#define SERIAL_TX_PIN 18      // Connected to Mega RX Pin 17
#define SERIAL_BAUD_RATE 9600 // Baud rate must match Mega's ESP32_SERIAL_BAUD

// Message protocol constants
#define START_CHAR '<'
#define END_CHAR '>'
#define MAX_BUFFER_SIZE 64
#define MAX_RFID_TAG_LENGTH 12 // Ensure this matches MOCK_RFID_TAG length on Mega if testing

// Command identifiers
#define CMD_MOTION 'M'
#define CMD_RFID 'R'
#define CMD_EMERGENCY 'E'

// --- Extern Declarations (for access from main.cpp) ---
extern bool motionDetected;
extern bool rfidDetected;
extern bool emergencyDetected;
extern char rfidTag[MAX_RFID_TAG_LENGTH + 1];

// Function declarations
void setupSerialHandler();
void processSerialData();
void parseSerialMessage(const char *message, size_t length);
void clearSerialFlags();

#endif // SERIAL_HANDLER_H
