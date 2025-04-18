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
