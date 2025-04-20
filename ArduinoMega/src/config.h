#ifndef CONFIG_H
#define CONFIG_H

// === Pin Definitions ===

// Input Pins
#define MOTION_INPUT_PIN 5
#define RFID_INPUT_PIN 6 // Active HIGH (no pull-up resistor required)
#define EMERGENCY_PIN 7   // Active LOW

// Output Pins
#define SERVO_TRIGGER_OUT_PIN 4
#define MOTION_SIGNAL_OUTPUT_PIN 8
#define RFID_SIGNAL_OUTPUT_PIN 9

// Serial Port Pins (Fixed on Mega, defined for clarity)
#define ESP32_SERIAL_TX_PIN 18
#define ESP32_SERIAL_RX_PIN 19

// === Serial Configuration ===
#define DEBUG_SERIAL_BAUD 115200 // Baud rate for Serial (USB Debugging)

// === Timing Constants ===
#define SENSOR_DEBOUNCE_TIME_MS 500   // Debounce time for sensors (ms) - *May require tuning*
#define SERVO_TRIGGER_DURATION_MS 100 // How long to hold the servo trigger signal HIGH (ms) - *May require tuning*
#define RFID_ACTIVITY_TIMEOUT_MS 1000 // Consider RFID stopped if input is LOW for this long

// === Mock RFID Value ===
#define MOCK_RFID_TAG "FAKE123" // Mock RFID tag to send

#endif // CONFIG_H
