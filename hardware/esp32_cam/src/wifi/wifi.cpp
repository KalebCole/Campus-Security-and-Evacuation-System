#include "wifi.h"

// WiFi status variables
bool wifiConnected = false;
unsigned long lastConnectionAttempt = 0;
const unsigned long CONNECTION_RETRY_DELAY = 5000; // 5 seconds between retry attempts

/**
 * Connect to WiFi using credentials from config.h
 * Returns true on success, false otherwise
 */
bool connectToWiFi()
{
    Serial.println("Connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    unsigned long wifiStartTime = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - wifiStartTime < WIFI_TIMEOUT))
    {
        Serial.print(".");
        delay(WIFI_ATTEMPT_DELAY);
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        wifiConnected = true;
        Serial.println("\nWiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        return true;
    }
    else
    {
        wifiConnected = false;
        Serial.println("\nWiFi connection failed!");
        WiFi.disconnect(true);
        delay(100);
        return false;
    }
}

/**
 * Initial WiFi setup
 */
void setupWifi()
{
    WiFi.mode(WIFI_STA);
    lastConnectionAttempt = 0; // Force immediate connection attempt
    checkWiFiConnection();
}

/**
 * Check WiFi connection status and reconnect if needed
 * Should be called periodically from the main loop
 */
void checkWiFiConnection()
{
    unsigned long currentTime = millis();

    // Check if WiFi is disconnected and retry connecting after delay
    if (!isWiFiConnected() && (currentTime - lastConnectionAttempt >= CONNECTION_RETRY_DELAY))
    {
        Serial.println("WiFi disconnected, reconnecting...");
        connectToWiFi();
        lastConnectionAttempt = currentTime;
    }
}

/**
 * Returns the current WiFi connection status
 */
bool isWiFiConnected()
{
    return WiFi.status() == WL_CONNECTED;
}
