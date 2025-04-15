#ifndef CONFIG_H
#define CONFIG_H

// === Pin Definitions ===

// Input Pins
#define MOTION_SENSOR_PIN 22 // #TODO: determine the pin
#define RFID_SENSOR_PIN 24   // #TODO: this will be a pull-up resistor
#define EMERGENCY_PIN 26     // #TODO: determine the pin

// Output Pins
#define MOTION_SIGNAL_OUT_PIN 30 // #TODO: determine the pin
#define RFID_SIGNAL_OUT_PIN 32   // #TODO: determine the pin
#define SERVO_TRIGGER_OUT_PIN 34 // #TODO: determine the pin

// Status LED (Optional, uses built-in LED on Mega)
#define STATUS_LED_PIN LED_BUILTIN

// === WiFi Configuration ===
#define WIFI_SSID "iPod Mini"      // Replace with your network SSID
#define WIFI_PASSWORD "H0t$p0t!"   // Replace with your network Password
#define WIFI_MAX_ATTEMPTS 20       // Attempts during initial connection
#define WIFI_ATTEMPT_DELAY 500     // Delay between initial attempts (ms)
#define WIFI_RECONNECT_DELAY 10000 // How often to attempt WiFi reconnect if lost (ms)

// === MQTT Configuration ===
#define MQTT_BROKER "172.20.10.2" // Replace with your MQTT Broker IP
#define MQTT_PORT 1883
#define MQTT_CLIENT_ID "arduino_mega_controller" // Unique client ID
#define MQTT_RECONNECT_DELAY 5000                // Delay before retrying MQTT connection if lost (ms)

// MQTT Topics
#define TOPIC_EMERGENCY "campus/security/emergency" // Mega publishes here
#define TOPIC_UNLOCK "campus/security/unlock"       // Mega subscribes here

// === Timing Constants ===
#define SENSOR_DEBOUNCE_TIME 50    // Debounce time for sensors (ms) - Reduced slightly
#define SIGNAL_PULSE_DURATION 100  // Duration for signal pulses if using pulse method (ms)
#define SERVO_TRIGGER_DURATION 500 // How long to hold the servo trigger signal HIGH (ms)
#define LOOP_DELAY_MS 10           // Small delay in main loop (ms)

// === Mock RFID Values (for logging only) ===
const char *const MOCK_RFIDS[] = {
    "MEGA_RFID_01",
    "MEGA_RFID_02",
    "MEGA_RFID_03"};
#define NUM_MOCK_RFIDS (sizeof(MOCK_RFIDS) / sizeof(MOCK_RFIDS[0]))

#endif // CONFIG_H
