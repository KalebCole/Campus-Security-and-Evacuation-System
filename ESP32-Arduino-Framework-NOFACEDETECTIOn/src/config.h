#ifndef CONFIG_H
#define CONFIG_H

// State machine states
enum StateMachine
{
    IDLE,           // Camera off, minimal power
    ACTIVE_WAITING, // Camera on, ready for capture
    ACTIVE_SESSION, // Processing and sending image
    EMERGENCY,      // System paused
    ERROR           // Connection/hardware issues
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
#define WIFI_SSID "iPod Mini"
#define WIFI_PASSWORD "H0t$p0t!"
#define WIFI_TIMEOUT 10000     // 10 seconds timeout
#define WIFI_ATTEMPT_DELAY 500 // 500ms between attempts

// MQTT Configuration
#define MQTT_BROKER "172.20.10.2"
#define MQTT_PORT 1883
#define MQTT_CLIENT_ID "esp32_cam"
#define MQTT_BUFFER_SIZE 30000 // Buffer size for MQTT messages

// MQTT Topics
#define TOPIC_EMERGENCY "campus/security/emergency"
#define TOPIC_RFID "campus/security/rfid"
#define TOPIC_STATUS "campus/security/status"
#define TOPIC_SESSION "campus/security/session"

// Timing Constants
#define LED_NORMAL_BLINK 1000   // Normal blink interval in ms
#define LED_ERROR_BLINK 200     // Error blink interval in ms
#define LED_SESSION_BLINK 500   // Session blink interval in ms
#define SESSION_TIMEOUT 10000   // 10 seconds session timeout
#define EMERGENCY_TIMEOUT 10000 // 10 seconds emergency timeout
#define RETRY_DELAY 5000        // 5 seconds between retry attempts

// External variable declarations
extern StateMachine currentState;
extern bool isEmergencyMode;
extern unsigned long lastStateChange;
extern unsigned long lastLedToggle;
extern bool ledState;

#endif // CONFIG_H