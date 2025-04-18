#ifndef CONFIG_H
#define CONFIG_H

// === Pin Definitions ===

// Input Pins
#define MOTION_SENSOR_PIN 5
#define RFID_SENSOR_PIN 6 // Active HIGH (no pull-up resistor required)
#define EMERGENCY_PIN 7   // Active LOW

// Output Pins
#define SERVO_TRIGGER_OUT_PIN 4

// Serial Port Pins (Fixed on Mega, defined for clarity)
// #define MKR_SERIAL_TX_PIN 18   // Serial1 TX - Unused
// #define MKR_SERIAL_RX_PIN 19   // Serial1 RX - Unused
#define ESP32_SERIAL_TX_PIN 16 // Serial2 TX
#define ESP32_SERIAL_RX_PIN 17 // Serial2 RX

// === Serial Configuration ===
#define DEBUG_SERIAL_BAUD 115200 // Baud rate for Serial (USB Debugging)
// #define MKR_SERIAL_BAUD 9600     // Baud rate for Serial1 - Unused
#define ESP32_SERIAL_BAUD 9600 // Baud rate for Serial2 (ESP32-CAM)

// === Timing Constants ===
#define SENSOR_DEBOUNCE_TIME_MS 500   // Debounce time for sensors (ms) - *May require tuning*
#define SERVO_TRIGGER_DURATION_MS 100 // How long to hold the servo trigger signal HIGH (ms) - *May require tuning*

// === Mock RFID Value ===
#define MOCK_RFID_TAG "FAKE123" // Mock RFID tag to send

#endif // CONFIG_H
