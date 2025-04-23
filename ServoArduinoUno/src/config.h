#ifndef CONFIG_H
#define CONFIG_H

// === Pin Definitions ===
#define EMERGENCY_TRIGGER_PIN 5 // Input pin receiving signal from Arduino Mega (Pin 4)
#define SERVO_PIN 9             // Output pin for the servo motor

// === Servo Parameters ===
#define SERVO_UNLOCK_ANGLE 95      // Angle in degrees for the unlocked position
#define SERVO_LOCK_ANGLE 180       // Angle in degrees for the locked position
#define SERVO_UNLOCK_TIMEOUT 15000 // Time in milliseconds to stay unlocked (15 seconds)

// === Serial Configuration ===

#define DEBUG_SERIAL_BAUD 115200 // Baud rate for Serial debugging

// WiFi Configuration
// #define WIFI_SSID "iPod Mini" // Removed - Defined via build flags
// #define WIFI_PASSWORD "H0t$p0t!" // Removed - Defined via build flags
#define WIFI_TIMEOUT 10000     // 10 seconds timeout
#define WIFI_ATTEMPT_DELAY 500 // 500ms between attempts

// MQTT Configuration
// TODO: update the mqtt broker address to the cloud broker on fly.io
// hostname assigned to it:         #define MQTT_BROKER "campus-security-evacuation-system.fly.dev"
// #define MQTT_BROKER "172.20.10.2"
// #define MQTT_PORT 1883
// EMQX MQTT Serverless Instance
#define MQTT_BROKER "z8002768.ala.us-east-1.emqxsl.com"
#define MQTT_PORT 8883
#define MQTT_CLIENT_ID "servo-arduino"
// MQTT_USERNAME and MQTT_PASSWORD will be defined via build flags

#define MQTT_BUFFER_SIZE 500

// MQTT Topics
#define TOPIC_UNLOCK "campus/security/unlock"       // Topic to receive unlock commands
#define TOPIC_EMERGENCY "campus/security/emergency" // Topic to publish emergency events

// EMQX CA Certificate (PEM Format)
extern const char* EMQX_CA_CERT_PEM;

// --- Deprecated/Consolidated --- Keep only needed defines
// #define SERVO_LOCKED_POSITION 180 // Duplicate of SERVO_LOCK_ANGLE
// #define SERVO_UNLOCKED_POSITION 95 // Duplicate of SERVO_UNLOCK_ANGLE

#endif // CONFIG_H