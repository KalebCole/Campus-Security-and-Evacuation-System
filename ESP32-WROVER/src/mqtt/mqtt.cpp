#include "mqtt.h"
#include <WiFiClientSecure.h> // Include for secure client

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

// MQTT client objects (Use Secure Client)
WiFiClientSecure espClientSecure;         // Changed from WiFiClient
PubSubClient mqttClient(espClientSecure); // Point PubSubClient to the secure client
bool mqttConnected = false;

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

    // Handle emergency messages
    if (strcmp(topic, TOPIC_EMERGENCY) == 0)
    {
        Serial.println("Emergency message received!");
        // Emergency handling logic will be implemented in the state machine
    }
}

/**
 * Connect to MQTT Broker
 * Returns true on success, false otherwise
 */
bool connectToMQTT()
{
    // Set CA Certificate for the secure client BEFORE connecting
    Serial.println("Setting CA Certificate for MQTT...");
    espClientSecure.setCACert(EMQX_CA_CERT_PEM);

    mqttClient.setBufferSize(MQTT_BUFFER_SIZE);
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);

    Serial.print("Attempting MQTT connection (Username: ");
    Serial.print(MQTT_USERNAME); // Username defined via build_flags
    Serial.println(")...");

    // Connect using Client ID, Username, and Password
    if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD))
    {
        mqttConnected = true;
        Serial.println("MQTT connected");

        // Subscribe to required topics
        mqttClient.subscribe(TOPIC_EMERGENCY);

        // Publish online status
        StaticJsonDocument<100> doc;
        doc["device_id"] = MQTT_CLIENT_ID;
        doc["status"] = "online";
        String output;
        serializeJson(doc, output);
        mqttClient.publish(TOPIC_SESSION, output.c_str());
        Serial.println("Published online status.");
        return true;
    }
    else
    {
        mqttConnected = false;
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
    connectToMQTT();
}

/**
 * Check MQTT connection status and reconnect if needed
 * Should be called periodically from the main loop
 */
void checkMQTTConnection()
{
    if (!mqttClient.connected())
    {
        mqttConnected = false;
        Serial.println("MQTT disconnected, reconnecting...");
        connectToMQTT();
    }
    else
    {
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
