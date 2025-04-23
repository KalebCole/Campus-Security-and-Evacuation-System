#include "mqtt.h"
#include <WiFiS3.h>
#include <PubSubClient.h>
#include "../wifi/wifi.h"

// Define the CA Certificate here (moved from config.h)
const char *EMQX_CA_CERT_PEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDrzCCApegAwIBAgIQCDvgVpBCRrGhdWrJWZHHSjANBgkqhkiG9w0BAQUFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBD
QTAeFw0wNjExMTAwMDAwMDBaFw0zMTExMTAwMDAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IENBMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4jvhEXLeqKTTo1eqUKKPC3eQyaKl7hLOllsB
CSDMAZOnTjC3U/dDxGkAV53ijSLdhwZAAIEJzs4bg7/fzTtxRuLWZscFs3YnFo97
nh6Vfe63SKMI2tavegw5BmV/Sl0fvBf4q77uKNd0f3p4mVmFaG5cIzJLv07A6Fpt
43C/dxC//AH2hdmoRBBYMql1GNXRor5H4idq9Joz+EkIYIvUX7Q6hL+hqkpMfT7P
T19sdl6gSzeRntwi5m3OFBqOasv+zbMUZBfHWymeMr/y7vrTC0LUq7dBMtoM1O/4
gdW7jVg/tRvoSSiicNoxBN33shbyTApOB6jtSj1etX+jkMOvJwIDAQABo2MwYTAO
BgNVHQ8BAf8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUA95QNVbR
TLtm8KPiGxvDl7I90VUwHwYDVR0jBBgwFoAUA95QNVbRTLtm8KPiGxvDl7I90VUw
DQYJKoZIhvcNAQEFBQADggEBAMucN6pIExIK+t1EnE9SsPTfrgT1eXkIoyQY/Esr
hMAtudXH/vTBH1jLuG2cenTnmCmrEbXjcKChzUyImZOMkXDiqw8cvpOp/2PV5Adg
06O/nVsJ8dWO41P0jmP6P6fbtGbfYmbW0W5BjfIttep3Sp+dWOIrWcBAI+0tKIJF
PnlUkiaY4IBIqDfv8NZ5YBberOgOzW6sRBc4L0na4UU+Krk2U886UAb3LujEV0ls
YSEY1QSteDwsOoBrp+uvFRTp2InBuThs4pFsiv9kuXclVzDAGySj4dzp30d8tbQk
CAUw7C29C79Fv1C5qfPrmAESrciIxpg0X40KPMbp1ZWVbd4=
-----END CERTIFICATE-----
)EOF";

// MQTT client objects (defined in main.cpp, declared extern in mqtt.h)
// We need the extern declarations here to use them
extern WiFiSSLClient wifiClient;
extern PubSubClient mqttClient;

// set the certification

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
    // Set CA Certificate for the secure client BEFORE connecting
    Serial.println("Setting CA Certificate for MQTT..."); // Re-added for WiFiClientSecure
    wifiClient.setCACert(EMQX_CA_CERT_PEM);               // Re-added for WiFiClientSecure

    mqttClient.setBufferSize(MQTT_BUFFER_SIZE);
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);

    Serial.print("Attempting MQTT connection (Username: ");
    Serial.print(MQTT_USERNAME); // Log username
    Serial.println(")...");

    // Connect using Client ID, Username, and Password from build flags
    if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD))
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
