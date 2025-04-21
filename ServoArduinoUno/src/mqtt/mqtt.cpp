#include "mqtt.h"
#include <WiFiS3.h>
#include <PubSubClient.h>
#include "../wifi/wifi.h"

// MQTT client objects (defined in main.cpp, declared extern in mqtt.h)
// We need the extern declarations here to use them
extern WiFiClient wifiClient;
extern PubSubClient mqttClient;

// MQTT status variables
// bool mqttConnected = false; // Removed - Rely only on mqttClient.connected()
unsigned long lastMQTTAttemptTime = 0;
const unsigned long MQTT_RETRY_DELAY = 5000; // 5 seconds between MQTT retry attempts

/**
 * Basic MQTT Callback function
 */
void mqttCallback(char *topic, byte *payload, unsigned int length)
{
    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("] ");

    // Convert payload to string for easier handling
    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';
    Serial.println(message);

    // Handle unlock command
    if (strcmp(topic, TOPIC_EMERGENCY) == 0)
    {
        Serial.println("Received message on EMERGENCY topic (publishing only).");
        // Currently no action needed on receiving /emergency, we only publish to it.
    }
    else if (strcmp(topic, TOPIC_UNLOCK) == 0)
    {
        Serial.println("Received UNLOCK command via MQTT.");
        unlockServo(); // Call the function defined in main.cpp
    }
}

/**
 * Connect to MQTT Broker
 * Returns true on success, false otherwise
 */
bool connectToMQTT()
{
    mqttClient.setBufferSize(MQTT_BUFFER_SIZE);
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);

    Serial.println("Attempting MQTT connection...");
    if (mqttClient.connect(MQTT_CLIENT_ID))
    {
        // mqttConnected = true; // Removed - Rely on mqttClient.connected()
        Serial.println("MQTT connected");

        // Subscribe to required topics
        mqttClient.subscribe(TOPIC_UNLOCK);

        // Publish online status to emergency topic
        StaticJsonDocument<100> doc;
        doc["device_id"] = MQTT_CLIENT_ID;
        doc["status"] = "online";
        String output;
        serializeJson(doc, output);
        mqttClient.publish(TOPIC_EMERGENCY, output.c_str());

        Serial.println("Published online status.");
        return true;
    }
    else
    {
        // mqttConnected = false; // Removed - Rely on mqttClient.connected()
        Serial.print("MQTT connection failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" ");
        return false;
    }
}

/**
 * Initial MQTT setup
 */
void setupMQTT()
{
    // connectToMQTT(); // Removed: Don't block setup, let loop handle first check.
    lastMQTTAttemptTime = 0; // Allow first attempt in loop immediately if WiFi is ready
}

/**
 * Check MQTT connection status and reconnect if needed
 * Should be called periodically from the main loop
 */
void checkMQTTConnection()
{
    unsigned long currentTime = millis();

    // Only attempt MQTT connection if WiFi is connected and we're not already connected
    if (!mqttClient.connected() && isWiFiConnected()) // Check WiFi status first!
    {
        // Check if enough time has passed since the last attempt
        if (currentTime - lastMQTTAttemptTime >= MQTT_RETRY_DELAY)
        {
            Serial.println("WiFi connected, attempting MQTT connection...");
            connectToMQTT();                   // Attempt connection (this has a short internal block)
            lastMQTTAttemptTime = currentTime; // Update last attempt time regardless of success
        }
    }
    else
    {
        // If connected, maintain the connection and process messages
        mqttClient.loop(); // Process MQTT messages
    }
}

/**
 * Returns the current MQTT connection status
 */
bool isMQTTConnected()
{
    return mqttClient.connected();
}
