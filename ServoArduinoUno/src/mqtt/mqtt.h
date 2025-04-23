#ifndef MQTT_H
#define MQTT_H

#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <WiFiS3.h>
#include <WiFiSSLClient.h>
#include "../config.h"

// Function declarations
void mqttCallback(char *topic, byte *payload, unsigned int length);
bool connectToMQTT();
void setupMQTT();
bool isMQTTConnected();
void checkMQTTConnection();

// Allow MQTT module to call unlockServo defined in main.cpp
extern void unlockServo();

// MQTT client declaration
extern WiFiSSLClient wifiClient;
extern PubSubClient mqttClient;

// MQTT status variable
// extern bool mqttConnected; // Removed - Rely on mqttClient.connected()

#endif // MQTT_H
