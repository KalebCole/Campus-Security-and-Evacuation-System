#include <WiFiS3.h>       // For Arduino Uno R4 WiFi networking
#include <PubSubClient.h> // For MQTT communication
#include <Servo.h>        // For controlling the servo motor
#include <ArduinoJson.h>  // For creating JSON status messages
#include "wifi/wifi.h"
#include "mqtt/mqtt.h"
#include "config.h"

// --- Global Objects ---
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
Servo myServo;

// --- Global State Variables ---
unsigned long unlockStartTime = 0; // Stores the time when the servo was unlocked
bool isUnlocked = false;           // Tracks if the servo is currently in the unlocked state
int lastEmergencyPinState = LOW;   // Track last known state of emergency pin

// --- Function Declarations ---
void lockServo();
void unlockServo();
void publishEmergencyStatus();

// --- Setup Function ---
void setup()
{
  Serial.begin(DEBUG_SERIAL_BAUD);
  while (!Serial)
    ; // Wait for Serial monitor
  Serial.println("Starting Servo MQTT Controller...");

  // Initialize Servo
  myServo.attach(SERVO_PIN);
  Serial.print("Initializing servo to locked position (");
  Serial.print(SERVO_LOCK_ANGLE);
  Serial.println(" degrees)...");
  myServo.write(SERVO_LOCK_ANGLE); // Start in the locked position
  isUnlocked = false;              // Ensure state is correct
  delay(500);                      // Give servo time to move

  // Configure Emergency Trigger Pin
  pinMode(EMERGENCY_TRIGGER_PIN, INPUT);
  lastEmergencyPinState = digitalRead(EMERGENCY_TRIGGER_PIN); // Read initial state
  Serial.print("Emergency Trigger Pin (");
  Serial.print(EMERGENCY_TRIGGER_PIN);
  Serial.print(") configured as INPUT. Initial state: ");
  Serial.println(lastEmergencyPinState == HIGH ? "HIGH" : "LOW");

  // Initialize WiFi
  setupWifi();

  // Configure MQTT
  setupMQTT();
}

// --- Helper Functions ---

/**
 * @brief Locks the servo by moving it to the defined lock angle.
 */
void lockServo()
{
  myServo.write(SERVO_LOCK_ANGLE);
  isUnlocked = false;
  Serial.println("Servo LOCKED.");
  // No status MQTT publish per user request
}

/**
 * @brief Unlocks the servo by moving it to the defined unlock angle
 *        and starts the relock timer.
 */
void unlockServo()
{
  myServo.write(SERVO_UNLOCK_ANGLE);
  isUnlocked = true;
  unlockStartTime = millis(); // Start the timer for automatic relock
  Serial.println("Servo UNLOCKED via trigger/MQTT.");
  // No status MQTT publish per user request
}


/**
 * @brief Publishes an emergency event message to the MQTT broker.
 */
void publishEmergencyStatus()
{
  if (!mqttClient.connected())
  { // Check MQTT connection before publishing
    Serial.println("WARN: Cannot publish emergency status, MQTT not connected.");
    return;
  }
  StaticJsonDocument<128> doc; // Allocate JSON document on the stack
  doc["device_id"] = MQTT_CLIENT_ID;
  doc["event"] = "emergency_triggered";
  doc["timestamp"] = millis();

  char buffer[128];
  size_t n = serializeJson(doc, buffer);

  if (n > 0)
  {
    if (mqttClient.publish(TOPIC_EMERGENCY, buffer, n))
    {
      Serial.println("Published emergency status to MQTT.");
    }
    else
    {
      Serial.println("ERROR: Failed to publish emergency status to MQTT.");
    }
  }
  else
  {
    Serial.println("ERROR: Failed to serialize emergency JSON.");
  }
}

// --- Main Loop ---
void loop()
{
  // print that we are in the loop
  // Serial.println("BEFORE CONNECTING TO WIFI");
  // Ensure WiFi/MQTT connections are maintained and process MQTT messages
  checkWiFiConnection(); // From wifi.cpp
  checkMQTTConnection(); // From mqtt.cpp (includes mqttClient.loop())
  // Serial.println("AFTER CONNECTING TO WIFI");
  // Check Emergency Trigger Pin (Pin 5)
  int currentEmergencyPinState = digitalRead(EMERGENCY_TRIGGER_PIN);
  // Serial.print("Current Emergency Pin State: ");
  // Serial.println(currentEmergencyPinState);
  // Check for a rising edge (LOW to HIGH transition)
  if (currentEmergencyPinState == HIGH && lastEmergencyPinState == LOW)
  {
    Serial.println("Emergency trigger detected (Pin 5 HIGH)!");
    unlockServo();            // Unlock the servo
    publishEmergencyStatus(); // Publish the emergency message
  }
  // Update the last known state for the next loop iteration
  lastEmergencyPinState = currentEmergencyPinState;

  // Check if the unlock timeout has expired (only if it's currently unlocked)
  if (isUnlocked && (millis() - unlockStartTime >= SERVO_UNLOCK_TIMEOUT))
  {
    Serial.println("Unlock timeout reached. Locking servo.");
    lockServo();
  }

  // Small delay to prevent busy-waiting and allow ESP32-S3 co-processor tasks (if applicable)
  // Also helps prevent spamming reads/checks in tight loop
  delay(10);
}