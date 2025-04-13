#ifndef CONFIG_H
#define CONFIG_H

// Pin Definitions
#define MOTION_PIN 5
#define EMERGENCY_PIN 3
#define RFID_PIN 2
#define UNLOCK_PIN 4

// WiFi Configuration
#define WIFI_SSID "iPod Mini"
#define WIFI_PASSWORD "H0t$p0t!"
#define WIFI_MAX_ATTEMPTS 10
#define WIFI_ATTEMPT_DELAY 500

// MQTT Configuration
#define MQTT_BROKER "172.20.10.2"
#define MQTT_PORT 1883
#define MQTT_CLIENT_ID "arduino_uno_r4"

// MQTT Topics
#define TOPIC_EMERGENCY "campus/security/emergency"
#define TOPIC_UNLOCK "campus/security/unlock"
#define TOPIC_RFID "campus/security/rfid"

// Timing Constants
#define LED_NORMAL_BLINK 1000      // Normal blink interval in ms
#define LED_ERROR_BLINK 200        // Error blink interval in ms
#define LED_RFID_BLINK 100         // RFID feedback blink duration
#define RFID_DEBOUNCE_TIME 1000    // Debounce time for RFID readings
#define MOTION_DEBOUNCE 1000       // Debounce time for motion sensor
#define UNLOCK_SIGNAL_DURATION 500 // Duration of unlock signal
#define EMERGENCY_TIMEOUT_MS 10000 // Emergency mode timeout (10 seconds)

// Mock RFID Values for Testing
const char *const MOCK_RFIDS[] = {
    "A1B2C3D4",
    "E5F6G7H8",
    "I9J0K1L2"};
#define NUM_MOCK_RFIDS (sizeof(MOCK_RFIDS) / sizeof(MOCK_RFIDS[0]))

// External variable declarations
extern bool isEmergencyMode;
extern unsigned long lastLedToggle;
extern bool ledState;
extern unsigned long lastRFIDCheck;
extern unsigned long unlockStartTime;
extern bool unlockInProgress;
extern unsigned long lastMotionCheck;
extern bool motionDetected;
extern unsigned long emergencyStartTime; // Added for emergency timeout tracking

#endif // CONFIG_H
