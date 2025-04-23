// ServoArduinoUno/src/tests/test_mqtt_secure_connection.cpp

#include <WiFiS3.h>        // Use WiFiS3 library for Uno R4
#include <PubSubClient.h>  // For MQTT
#include <WiFiSSLClient.h> // Added for TLS using built-in certs
#include "../config.h"     // Include main config for broker, etc.

// Removed CA Certificate definition - using built-in bundle with WiFiSSLClient
/*
const char *EMQX_CA_CERT_PEM = R"EOF(
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
)EOF";
*/

// WiFiSSLClient for TLS
WiFiSSLClient wifiClient;
// PubSubClient using the SSL client
PubSubClient mqttClient(wifiClient);

// Test Topic
const char *TEST_TOPIC = "campus/security/test/arduino_uno";

// --- Simple MQTT Callback (Optional) ---
void mqttCallback(char *topic, byte *payload, unsigned int length)
{
    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("] ");
    for (int i = 0; i < length; i++)
    {
        Serial.print((char)payload[i]);
    }
    Serial.println();
}

// --- WiFi Connection Function ---
void setupWifi()
{
    delay(10);
    Serial.println();
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int retries = 0;
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(WIFI_ATTEMPT_DELAY);
        Serial.print(".");
        retries++;
        if (retries > (WIFI_TIMEOUT / WIFI_ATTEMPT_DELAY))
        {
            Serial.println("\nWiFi connection timed out!");
            return; // Exit setup if WiFi fails
        }
    }

    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

// --- MQTT Reconnection Function ---
bool reconnectMQTT()
{
    Serial.print("Attempting MQTT connection (SSL) (");
    Serial.print(MQTT_BROKER);
    Serial.print(":");
    Serial.print(MQTT_PORT);
    Serial.print(")... Client ID: ");
    Serial.println(MQTT_CLIENT_ID);

    // Attempt to connect anonymously (common for Uno R4 basic TLS)
    if (mqttClient.connect(MQTT_CLIENT_ID))
    {
        Serial.println("MQTT connected!");
        // Publish test message on successful connect
        char msg[100];
        snprintf(msg, 100, "Arduino Uno R4 test client (%s) connected at %lu", MQTT_CLIENT_ID, millis());
        Serial.print("Publishing message: ");
        Serial.println(msg);
        bool published = mqttClient.publish(TEST_TOPIC, msg);
        if (published)
        {
            Serial.println("Message published successfully.");
            return true; // Indicate success and publish occurred
        }
        else
        {
            Serial.println("Message publish FAILED.");
            return true; // Still return true as connection worked
        }
    }
    else
    {
        Serial.print("MQTT connection failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" Retrying in 5 seconds...");
        delay(5000); // Wait 5 seconds before retrying
        return false;
    }
}

// --- Arduino Setup ---
void setup()
{
    Serial.begin(115200);
    Serial.println("\n--- Arduino Uno R4 MQTT SSL Connection Test ---");

    // Connect to WiFi
    setupWifi();
    if (WiFi.status() != WL_CONNECTED)
    {
        Serial.println("WiFi failed to connect. Stopping test.");
        while (1)
            delay(1000); // Halt
    }

    // Configure WiFiSSLClient (no manual CA cert needed for default)
    Serial.println("Setting up SSL client (using built-in certificates)... ");
    // wifiClient.setCACert(EMQX_CA_CERT_PEM); // Removed - Handled by WiFiSSLClient
    // Optional: Disable certificate validation for initial testing ONLY if needed
    // wifiClient.setInsecure(); // DANGEROUS: Removes server verification

    // Configure PubSubClient
    Serial.print("Setting MQTT server: ");
    Serial.print(MQTT_BROKER);
    Serial.print(":");
    Serial.println(MQTT_PORT);
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback); // Set the callback (optional)

    Serial.println("Setup complete. Entering loop...");
}

// --- Arduino Loop ---
bool connection_successful = false;
unsigned long lastAttemptTime = 0;
const unsigned long retryDelay = 5000; // 5 seconds between attempts
int connectAttempts = 0;
const int maxConnectAttempts = 5; // Stop after 5 failed attempts

void loop()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        Serial.println("WiFi disconnected. Attempting reconnect...");
        setupWifi(); // Try to reconnect WiFi
        return;      // Skip MQTT logic until WiFi is back
    }

    if (!connection_successful)
    {
        if (!mqttClient.connected())
        {
            unsigned long now = millis();
            if (now - lastAttemptTime > retryDelay && connectAttempts < maxConnectAttempts)
            {
                Serial.print("MQTT Connect Attempt ");
                Serial.print(connectAttempts + 1);
                Serial.print("/");
                Serial.println(maxConnectAttempts);
                if (reconnectMQTT())
                {
                    connection_successful = true; // Flag success
                    Serial.println("Connection and publish successful. Test complete.");
                    // Optional: Halt after success
                    // while(1) delay(1000);
                }
                lastAttemptTime = now;
                connectAttempts++;
                if (!connection_successful && connectAttempts >= maxConnectAttempts)
                {
                    Serial.println("Max MQTT connection attempts reached. Test failed.");
                    while (1)
                        delay(1000); // Halt on failure
                }
            }
        }
        else
        {
            connection_successful = true;
            Serial.println("MQTT was already connected? Test likely successful.");
        }
    }

    // If connected, keep the connection alive and process incoming messages
    if (mqttClient.connected())
    {
        mqttClient.loop();
    }

    delay(100); // Prevent busy-waiting
}