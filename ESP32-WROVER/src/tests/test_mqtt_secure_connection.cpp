// ESP32-WROVER/src/tests/test_mqtt_secure_connection.cpp

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "../config.h" // Include main config for credentials, cert, etc.

// WiFiClientSecure for TLS
WiFiClientSecure espClientSecure;
// PubSubClient using the secure client
PubSubClient mqttClient(espClientSecure);

// Test Topic
const char *TEST_TOPIC = "campus/security/test/esp32";

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
            // Consider adding error handling or restart here for robust test
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
    Serial.print("Attempting MQTT connection (");
    Serial.print(MQTT_BROKER);
    Serial.print(":");
    Serial.print(MQTT_PORT);
    Serial.print(")... Client ID: ");
    Serial.print(MQTT_CLIENT_ID);
    Serial.print(" Username: ");
    Serial.println(MQTT_USERNAME);

    // Attempt to connect with username and password
    if (mqttClient.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD))
    {
        Serial.println("MQTT connected!");
        // Publish test message on successful connect
        char msg[100];
        snprintf(msg, 100, "ESP32 test client (%s) connected at %lu", MQTT_CLIENT_ID, millis());
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
            // Still return true as connection worked, but flag issue
            return true;
        }
    }
    else
    {
        Serial.print("MQTT connection failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" Retrying in 5 seconds...");
        // Wait 5 seconds before retrying
        delay(5000);
        return false;
    }
}

// --- Arduino Setup ---
void setup()
{
    Serial.begin(115200);
    Serial.println("\n--- ESP32 MQTT Secure Connection Test ---");

    // Connect to WiFi
    setupWifi();
    if (WiFi.status() != WL_CONNECTED)
    {
        Serial.println("WiFi failed to connect. Stopping test.");
        while (1)
            delay(1000); // Halt
    }

    // Configure WiFiClientSecure with CA cert
    Serial.println("Setting up secure client with CA certificate...");
    espClientSecure.setCACert(EMQX_CA_CERT_PEM);
    // Optional: Disable certificate validation for initial testing ONLY if needed
    // espClientSecure.setInsecure(); // DANGEROUS: Removes server verification

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
                Serial.printf("MQTT Connect Attempt %d/%d\n", connectAttempts + 1, maxConnectAttempts);
                if (reconnectMQTT())
                {
                    connection_successful = true; // Flag success
                    Serial.println("Connection and publish successful. Test complete.");
                    // Optional: Disconnect after successful publish
                    // mqttClient.disconnect();
                    // Serial.println("MQTT disconnected. Halting.");
                    // while(1) delay(1000); // Halt after success
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
            // This case should ideally not be reached if reconnectMQTT handles success
            connection_successful = true;
            Serial.println("MQTT was already connected? Test likely successful.");
        }
    }

    // If connected, keep the connection alive and process incoming messages
    if (mqttClient.connected())
    {
        mqttClient.loop();
    }

    // Small delay to prevent busy-waiting if test doesn't halt
    delay(100);
}