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
void connectToWiFi()
{
    Serial.println("Attempting to connect to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    // Non-blocking: Just start the connection attempt.
    // The checkWiFiConnection function will periodically check WiFi.status()
    // Note: WiFi.status() might return WL_CONNECTING during this phase.

    // No immediate return value or status check here.
    // We don't set wifiConnected flag here anymore.
}

/**
 * Initial WiFi setup
 */
void setupWifi()
{
    if (WiFi.status() == WL_NO_MODULE)
    {
        Serial.println("ERROR: Communication with WiFi module failed!");
        while (true)
            ; // Halt if no WiFi module
    }
    // WiFi.mode(WIFI_STA); // Removed - Not applicable/needed for WiFiS3
    lastConnectionAttempt = 0; // Force immediate connection attempt on first loop
    // checkWiFiConnection(); // Removed: Don't block setup, let loop handle first check.
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
