#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h> // Add for String type

// State machine states
enum StateMachine
{
    IDLE,          // Camera off, minimal power
    CONNECTING,    // Establishing WiFi and MQTT connections
    IMAGE_CAPTURE, // Camera active, capturing image
    SESSION,       // Active session with image capture
    EMERGENCY,     // System paused, emergency mode
    ERROR,         // Connection/hardware issues
    COOLDOWN       // Waiting period after a session before returning to IDLE
};

// LED Pin Definitions
#define LED_PIN 2   // Built-in LED (white LED next to the camera)
#define LED_FLASH 4 // Flash LED (larger LED on the back)

// Camera Pin Definitions
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 21
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y2_GPIO_NUM 4
#define Y3_GPIO_NUM 5
#define Y4_GPIO_NUM 18
#define Y5_GPIO_NUM 19
#define Y6_GPIO_NUM 36
#define Y7_GPIO_NUM 39
#define Y8_GPIO_NUM 34
#define Y9_GPIO_NUM 35
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// WiFi Configuration
#define WIFI_TIMEOUT 10000     // 10 seconds timeout
#define WIFI_ATTEMPT_DELAY 500 // 500ms between attempts

// MQTT Configuration
// TODO: update the mqtt broker address to the cloud broker on fly.io
// #define MQTT_BROKER "campus-security-evacuation-system.fly.dev"
// #define MQTT_BROKER "172.20.10.2"
// #define MQTT_PORT 1883
#define MQTT_BROKER "z8002768.ala.us-east-1.emqxsl.com"
#define MQTT_PORT 8883
#define MQTT_CLIENT_ID "esp32_cam"
// #define MQTT_USERNAME "YOUR_MQTT_USERNAME"
// #define MQTT_PASSWORD "YOUR_MQTT_PASSWORD"

#define MQTT_BUFFER_SIZE 30000 // Buffer size for MQTT messages

// MQTT Topics
#define TOPIC_EMERGENCY "campus/security/emergency"
#define TOPIC_RFID "campus/security/rfid"
#define TOPIC_SESSION "campus/security/session"

// EMQX CA Certificate (PEM Format)
extern const char *EMQX_CA_CERT_PEM;

// Timing Constants
const unsigned long LED_SLOW_BLINK = 1000;          // Slow blink interval in ms
const unsigned long LED_NORMAL_BLINK = 500;         // Normal blink interval in ms
const unsigned long LED_FAST_BLINK = 200;           // Fast blink interval in ms
const unsigned long LED_VERY_FAST_BLINK = 100;      // Very fast blink interval in ms
const unsigned long LED_ERROR_BLINK = 200;          // Error blink interval in ms
const unsigned long SESSION_TIMEOUT = 3000;         // 3 seconds session timeout
const unsigned long EMERGENCY_TIMEOUT = 10000;      // 10 seconds emergency timeout
const unsigned long FACE_DETECTION_TIMEOUT = 10000; // 10 seconds face detection timeout
const unsigned long RFID_TIMEOUT = 5000;            // 5 seconds RFID timeout
const unsigned long RETRY_DELAY = 5000;             // 5 seconds between retry attempts
const unsigned long MOTION_DEBOUNCE = 1000;         // 1 second debounce for motion sensor
const unsigned long IMAGE_CAPTURE_INTERVAL = 1000;  // 1 second between image captures
const unsigned long COOLDOWN_DURATION_MS = 5000;    // 5 seconds cooldown after session

// State Machine Timeouts (milliseconds)
#define RETRY_DELAY 5000          // Delay before retrying WiFi/MQTT connection
#define EMERGENCY_TIMEOUT 30000   // Duration of emergency state before returning to IDLE
#define RFID_WAIT_TIMEOUT_MS 5000 // Max time to wait in SESSION state for RFID data

// External variable declarations
extern StateMachine currentState;
extern bool isEmergencyMode;
extern unsigned long lastStateChange;
extern unsigned long lastLedToggle;
extern bool ledState;
extern bool motionDetected;
extern unsigned long lastMotionCheck;
extern unsigned long sessionStartTime;
extern String currentSessionId;
extern bool rfidDetected;

// --- GPIO Input Configuration (Replaces Serial Handler) ---
#define MOTION_INPUT_PIN 15 // Pin connected to Mega's motion output (via divider)
#define RFID_INPUT_PIN 2    // Pin connected to Mega's RFID output (via divider)

// --- Shared State Variables (GPIO Approach) ---
#define MAX_RFID_TAG_LENGTH 12
extern bool motionDetected; // Set by GPIO read in main.cpp, checked by state machine
extern bool rfidDetected;   // Set by GPIO read in main.cpp, checked by state machine
// extern char rfidTag[MAX_RFID_TAG_LENGTH + 1];

#define LED_BLINK_INTERVAL 500

#endif // CONFIG_H