#include "wifi.h"
// WiFiS3.h is now included via wifi.h, no need to duplicate here

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
        // WiFi.disconnect(true); // Removed per user request and library specifics
        delay(100);
        return false;
    }
}

/**
 * Initial WiFi setup
 */
void setupWifi()
{
    // Check if the WiFi module is detected
    if (WiFi.status() == WL_NO_MODULE)
    {
        Serial.println("ERROR: Communication with WiFi module failed!");
        // Stay in an infinite loop since network functionality is critical
        while (true)
            ;
    }
    // WiFi.mode(WIFI_STA); // Removed - Not applicable/needed for WiFiS3
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
