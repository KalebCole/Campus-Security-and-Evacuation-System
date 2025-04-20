#include <Arduino.h>
#include <WiFi.h>

// --- Merged Config ---
// WiFi Configuration (Copy relevant parts from config.h)
#define WIFI_SSID "iPod Mini"    // Replace with your SSID
#define WIFI_PASSWORD "H0t$p0t!" // Replace with your Password
#define WIFI_TIMEOUT 10000       // 10 seconds timeout
#define WIFI_ATTEMPT_DELAY 500   // 500ms between attempts

// --- Merged WiFi Logic (Adapted from wifi.cpp) ---
bool wifiConnected_test = false; // Use a different variable name to avoid potential conflicts
unsigned long lastConnectionAttempt_test = 0;
const unsigned long CONNECTION_RETRY_DELAY_test = 5000; // 5 seconds between retry attempts

// Connect to WiFi using credentials defined above
// Returns true on success, false otherwise
bool connectToWiFi_test()
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
        wifiConnected_test = true;
        Serial.println("\nWiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        return true;
    }
    else
    {
        wifiConnected_test = false;
        Serial.println("\nWiFi connection failed!");
        WiFi.disconnect(true);
        delay(100);
        return false;
    }
}

// Initial WiFi setup for the test
void setupWifi_test()
{
    WiFi.mode(WIFI_STA);
    lastConnectionAttempt_test = 0; // Force immediate connection attempt
    connectToWiFi_test();
}

// Check WiFi connection status and reconnect if needed
void checkWiFiConnection_test()
{
    unsigned long currentTime = millis();

    // Check if WiFi is disconnected and retry connecting after delay
    if (WiFi.status() != WL_CONNECTED && (currentTime - lastConnectionAttempt_test >= CONNECTION_RETRY_DELAY_test))
    {
        Serial.println("WiFi disconnected, reconnecting...");
        connectToWiFi_test();
        lastConnectionAttempt_test = currentTime;
    }
}

// --- Test Sketch Setup & Loop ---

void setup()
{
    Serial.begin(115200);
    while (!Serial)
        ;
    delay(2000); // Give time to open monitor
    Serial.println("\n--- WiFi Connection Test --- ");
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(WIFI_SSID);

    setupWifi_test(); // Run the merged setup logic
}

void loop()
{
    checkWiFiConnection_test(); // Continuously check and attempt reconnect if needed

    // Optionally print status periodically
    static unsigned long lastStatusPrint = 0;
    if (millis() - lastStatusPrint > 5000) // Print status every 5 seconds
    {
        if (WiFi.status() == WL_CONNECTED)
        {
            Serial.print("WiFi Status: Connected, IP: ");
            Serial.println(WiFi.localIP());
        }
        else
        {
            Serial.println("WiFi Status: Disconnected");
        }
        lastStatusPrint = millis();
    }

    delay(100); // Small delay in the loop
}