#ifndef WIFI_H
#define WIFI_H

#include <WiFiS3.h>
#include "../config.h"

// Function declarations
void connectToWiFi();
void checkWiFiConnection();
void setupWifi();
bool isWiFiConnected();

// WiFi status variables
// extern bool wifiConnected; // Removed - Rely only on isWiFiConnected()
extern unsigned long lastConnectionAttempt;

#endif // WIFI_H
