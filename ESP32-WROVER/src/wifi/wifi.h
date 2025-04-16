#ifndef WIFI_H
#define WIFI_H

#include <WiFi.h>
#include "../config.h"

// Function declarations
bool connectToWiFi();
void checkWiFiConnection();
void setupWifi();
bool isWiFiConnected();

// WiFi status variables
extern bool wifiConnected;
extern unsigned long lastConnectionAttempt;

#endif // WIFI_H
