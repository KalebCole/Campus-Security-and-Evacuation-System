#ifndef MQTT_H
#define MQTT_H

#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <WiFiClientSecure.h>
// #include <WiFi.h> // Include WiFiClientSecure in .cpp instead
#include "../config.h"

// Function declarations
void mqttCallback(char *topic, byte *payload, unsigned int length);
bool connectToMQTT();
void setupMQTT();
bool isMQTTConnected();
void checkMQTTConnection();

// MQTT client declaration (Use Secure Client)
extern WiFiClientSecure espClientSecure; // Changed from WiFiClient
extern PubSubClient mqttClient;

// MQTT status variable
extern bool mqttConnected;

#endif // MQTT_H
