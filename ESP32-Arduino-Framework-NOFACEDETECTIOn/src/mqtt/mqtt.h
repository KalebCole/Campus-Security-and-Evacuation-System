#ifndef MQTT_H
#define MQTT_H

#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include "../config.h"

// Function declarations
void mqttCallback(char *topic, byte *payload, unsigned int length);
bool connectToMQTT();
void setupMQTT();
bool isMQTTConnected();
void checkMQTTConnection();

// MQTT client declaration
extern WiFiClient espClient;
extern PubSubClient mqttClient;

// MQTT status variable
extern bool mqttConnected;

#endif // MQTT_H
