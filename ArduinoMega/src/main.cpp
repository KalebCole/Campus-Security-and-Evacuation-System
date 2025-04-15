#include <Arduino.h>
#include <WiFiS3.h> // Assuming Mega uses a compatible WiFi module like Uno R4 WiFi
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"

// === State Machine Definition ===
enum SystemState
{
  INIT,        // Initial setup phase (in setup())
  CONNECTING,  // Establishing WiFi/MQTT connection
  OPERATIONAL, // Normal operation: monitoring sensors, handling MQTT
  EMERGENCY,   // Emergency button activated
  ERROR_STATE  // Non-recoverable error
};
SystemState currentState = INIT; // Start in INIT, move to CONNECTING after setup

// === WiFi & MQTT Clients ===
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

// === Global State Variables ===
// Sensor states
unsigned long lastMotionCheck = 0;
bool motionDetectedState = false; // Current debounced state

unsigned long lastRFIDCheck = 0;
bool rfidDetectedState = false; // Current debounced state (LOW is detected)

// Emergency state
unsigned long lastEmergencyCheck = 0;
bool emergencyButtonState = false; // Current physical state of the button (debounced)
bool emergencyActive = false;      // Latched state indicating emergency mode is active

// Servo trigger state
unsigned long servoTriggerStartTime = 0;
bool servoTriggerActive = false;

// Connection state
unsigned long lastWifiCheck = 0;
unsigned long lastMqttAttempt = 0;

// === Function Declarations ===
// Core Logic
void log(const char *event, const char *message);
void checkEmergencyButton(); // Renamed from handleEmergencyButton
void handleConnectingState();
void handleOperationalState();
void handleEmergencyState();
void handleErrorState();
void updateStatusLED();

// Actions & Handlers
void setupWiFi();
void setupMQTT();
// void checkConnections(); // Logic integrated into handleConnectingState
void handleMQTTCallback(char *topic, byte *payload, unsigned int length);
void handleSensors();
void sendServoTriggerSignal();
void handleServoTrigger();
String getRandomRFID();

// === Setup ===
void setup()
{
  currentState = INIT;
  Serial.begin(115200);
  unsigned long startTime = millis();
  while (!Serial && millis() - startTime < 3000)
    ;
  log("INIT", "System starting...");

  // Configure Pins
  pinMode(MOTION_SENSOR_PIN, INPUT);
  pinMode(RFID_SENSOR_PIN, INPUT_PULLUP); // Assuming LOW detection
  pinMode(EMERGENCY_PIN, INPUT_PULLUP);   // Assuming LOW detection when pressed
  pinMode(MOTION_SIGNAL_OUT_PIN, OUTPUT);
  pinMode(RFID_SIGNAL_OUT_PIN, OUTPUT);
  pinMode(SERVO_TRIGGER_OUT_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);

  digitalWrite(MOTION_SIGNAL_OUT_PIN, LOW);
  digitalWrite(RFID_SIGNAL_OUT_PIN, LOW);
  digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
  digitalWrite(STATUS_LED_PIN, LOW);

  log("INIT", "Pins configured");

  // Initialize random seed
  randomSeed(analogRead(0));

  // Initialize Network/MQTT settings but don't connect yet
  setupMQTT(); // Sets server and callback

  log("INIT", "Setup complete. Transitioning to CONNECTING state.");
  currentState = CONNECTING; // Move to connecting state for the first loop()
}

// === Main Loop ===
void loop()
{
  // --- High Priority: Emergency Check ---
  // Check on every loop, regardless of state
  checkEmergencyButton(); // Updates emergencyButtonState (debounced)

  // Check for the *rising edge* of the emergency button press
  if (emergencyButtonState && !emergencyActive)
  {
    // --- Entering Emergency State ---
    log("EMERGENCY", "Emergency Button Pressed! Entering Emergency State.");
    emergencyActive = true; // Latch the emergency active flag
    currentState = EMERGENCY;

    // 1. IMMEDIATE ACTION: Trigger Servo Unlock (Network Independent)
    sendServoTriggerSignal();

    // 2. BEST EFFORT: Send MQTT Notification (Network Dependent)
    if (mqtt.connected())
    {
      StaticJsonDocument<200> doc;
      doc["device_id"] = MQTT_CLIENT_ID;
      doc["event"] = "emergency";
      doc["timestamp"] = millis();

      char buffer[200];
      serializeJson(doc, buffer);
      if (mqtt.publish(TOPIC_EMERGENCY, buffer))
      {
        log("MQTT", "Published Emergency message");
      }
      else
      {
        log("ERROR", "Failed to publish Emergency message while connected");
      }
    }
    else
    {
      log("EMERGENCY", "MQTT not connected, cannot send notification. Door triggered.");
    }
    // Skip regular state handling for this loop iteration as we just entered Emergency
  }
  else
  {
    // --- Regular State Handling (if not entering Emergency right now) ---
    switch (currentState)
    {
    case CONNECTING:
      handleConnectingState();
      break;
    case OPERATIONAL:
      handleOperationalState();
      break;
    case EMERGENCY: // Already in emergency state
      handleEmergencyState();
      break;
    case ERROR_STATE:
      handleErrorState();
      break;
    case INIT: // Should not be in INIT state during loop
    default:
      log("ERROR", "Reached invalid state in loop(). Resetting to CONNECTING.");
      currentState = CONNECTING;
      break;
    }
  }

  // --- Shared Logic ---
  // Ensure servo signal turns off after duration, regardless of state
  handleServoTrigger();
  // Update status LED based on current state and connectivity
  updateStatusLED();

  delay(LOOP_DELAY_MS); // Small delay
}

// === State Handlers ===

void handleConnectingState()
{
  // log("STATE", "Handling CONNECTING"); // Can be noisy
  unsigned long now = millis();

  // 1. Check/Establish WiFi Connection
  if (WiFi.status() != WL_CONNECTED)
  {
    // Only attempt connection periodically
    if (now - lastWifiCheck >= WIFI_RECONNECT_DELAY)
    {
      lastWifiCheck = now;
      log("WIFI", "WiFi disconnected. Attempting connect...");
      // Consider WiFi.disconnect() before begin? May help sometimes.
      // WiFi.disconnect();
      // delay(100);
      setupWiFi(); // Contains the blocking connection attempt logic
      if (currentState == ERROR_STATE)
        return;            // setupWiFi might transition to ERROR_STATE
      lastMqttAttempt = 0; // Force MQTT attempt if WiFi succeeds
    }
    return; // Don't try MQTT if WiFi isn't up
  }

  // 2. Check/Establish MQTT Connection (only if WiFi is connected)
  if (!mqtt.connected())
  {
    if (now - lastMqttAttempt >= MQTT_RECONNECT_DELAY)
    {
      lastMqttAttempt = now;
      log("MQTT", "WiFi connected. Attempting MQTT connection...");
      if (mqtt.connect(MQTT_CLIENT_ID))
      {
        log("MQTT", "Connected successfully!");
        log("MQTT", "Subscribing to Unlock topic...");
        if (mqtt.subscribe(TOPIC_UNLOCK))
        {
          log("MQTT", "Subscribed successfully!");
          log("STATE", "Connections established. Transitioning to OPERATIONAL.");
          currentState = OPERATIONAL; // Transition to normal operation
        }
        else
        {
          log("ERROR", "Failed to subscribe to Unlock topic! Disconnecting MQTT.");
          mqtt.disconnect(); // Don't proceed if subscription fails
        }
      }
      else
      {
        log("ERROR", "MQTT connection failed. Will retry...");
        // Stay in CONNECTING state
      }
    }
  }
  // If both WiFi and MQTT are connected, the transition to OPERATIONAL happens above.
}

void handleOperationalState()
{
  // log("STATE", "Handling OPERATIONAL"); // Can be noisy, enable if needed

  // 1. Check Connection Status (could be lost)
  if (WiFi.status() != WL_CONNECTED || !mqtt.connected())
  {
    log("WARN", "Connection lost in OPERATIONAL state. Transitioning to CONNECTING.");
    currentState = CONNECTING;
    return; // Exit operational handling
  }

  // 2. Process MQTT Messages
  mqtt.loop(); // Handles incoming messages and keepalives

  // 3. Handle Sensors and Update Signals
  handleSensors();

  // Note: Emergency check is done at the start of loop()
  // Note: Servo trigger turn-off is done at the end of loop()
}

void handleEmergencyState()
{
  // log("STATE", "Handling EMERGENCY"); // Can be noisy

  // Main purpose here is to check if the emergency condition is resolved
  // The checkEmergencyButton() function updates emergencyButtonState (debounced)
  if (!emergencyButtonState) // Button is released
  {
    log("EMERGENCY", "Emergency Button Released. Returning to CONNECTING state.");
    emergencyActive = false;   // Unlatch the state
    currentState = CONNECTING; // Go back to connecting to ensure network is okay
  }
  // We stay in EMERGENCY state as long as the button is held down (LOW).
  // Servo trigger is handled by handleServoTrigger() at the end of loop().
  // MQTT notification was sent on entry (best effort).
}

void handleErrorState()
{
  log("STATE", "Handling ERROR_STATE");
  // Indicate non-recoverable error. Usually requires manual reset.
  // Actions: Maybe solid LED, stop trying to connect.
  // For now, just logs and the LED handler will show solid ON.
}

// === Core Action & Utility Functions ===

void checkEmergencyButton()
{
  // Simple debounce for the emergency button
  static bool lastRawState = HIGH; // Assuming pull-up, HIGH is released
  static unsigned long lastDebounceTime = 0;
  bool reading = digitalRead(EMERGENCY_PIN);

  // If the switch changed, due to noise or pressing:
  if (reading != lastRawState)
  {
    // reset the debouncing timer
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > SENSOR_DEBOUNCE_TIME)
  {
    // whatever the reading is at, it's been there for longer than the debounce
    // delay, so take it as the actual current state:
    // if the button state has changed:
    if (reading != emergencyButtonState)
    {
      emergencyButtonState = reading;
      // Only log if you need to debug the button itself
      // log("DEBUG", emergencyButtonState == LOW ? "Emergency Button Pressed (Debounced)" : "Emergency Button Released (Debounced)");
    }
  }
  lastRawState = reading;
  // Note: Assumes LOW = Pressed because of INPUT_PULLUP.
  // emergencyButtonState will be LOW when pressed.
}

void handleSensors()
{
  unsigned long now = millis();

  // --- Motion Sensor --- (Assuming HIGH = Detected)
  static bool lastRawMotionState = LOW;
  static bool debouncedMotionState = LOW;
  static unsigned long lastMotionDebounceTime = 0;
  bool rawMotion = digitalRead(MOTION_SENSOR_PIN);

  if (rawMotion != lastRawMotionState)
  {
    lastMotionDebounceTime = millis();
  }
  if ((millis() - lastMotionDebounceTime) > SENSOR_DEBOUNCE_TIME)
  {
    if (rawMotion != debouncedMotionState)
    {
      debouncedMotionState = rawMotion;
      digitalWrite(MOTION_SIGNAL_OUT_PIN, debouncedMotionState); // Directly set output
      log("SENSOR", debouncedMotionState ? "Motion DETECTED" : "Motion CLEARED");
    }
  }
  lastRawMotionState = rawMotion;

  // --- RFID Sensor --- (Assuming LOW = Detected due to INPUT_PULLUP)
  static bool lastRawRfidState = HIGH; // High when not detected
  static bool debouncedRfidState = HIGH;
  static unsigned long lastRfidDebounceTime = 0;
  bool rawRfid = digitalRead(RFID_SENSOR_PIN);

  if (rawRfid != lastRawRfidState)
  {
    lastRfidDebounceTime = millis();
  }
  if ((millis() - lastRfidDebounceTime) > SENSOR_DEBOUNCE_TIME)
  {
    if (rawRfid != debouncedRfidState)
    {
      debouncedRfidState = rawRfid;
      bool rfidIsDetected = (debouncedRfidState == LOW); // LOW means detected
      digitalWrite(RFID_SIGNAL_OUT_PIN, rfidIsDetected); // Output HIGH when detected
      if (rfidIsDetected)
      {
        String mockRfid = getRandomRFID();
        log("SENSOR", "RFID DETECTED");
        log("RFID_MOCK", mockRfid.c_str());
      }
      else
      {
        log("SENSOR", "RFID CLEARED");
      }
    }
  }
  lastRawRfidState = rawRfid;
}

void sendServoTriggerSignal()
{
  if (!servoTriggerActive)
  {
    log("CONTROL", "Sending Servo Trigger Signal");
    digitalWrite(SERVO_TRIGGER_OUT_PIN, HIGH);
    servoTriggerStartTime = millis();
    servoTriggerActive = true;
  }
  else
  {
    // Avoid re-triggering if already active
    // log("CONTROL", "Servo Trigger already active, ignoring duplicate request");
  }
}

void handleServoTrigger()
{
  // This runs every loop to turn off the signal after the duration
  if (servoTriggerActive && (millis() - servoTriggerStartTime >= SERVO_TRIGGER_DURATION))
  {
    log("CONTROL", "Ending Servo Trigger Signal");
    digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
    servoTriggerActive = false;
  }
}

void setupWiFi()
{
  log("WIFI", "Connecting to WiFi...");

  if (WiFi.status() == WL_NO_MODULE)
  {
    log("ERROR", "WiFi module not found! Entering ERROR state.");
    currentState = ERROR_STATE;
    return; // Stop connection attempt
  }

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  // This is blocking, but necessary for initial connection.
  // Timeout handled by WIFI_MAX_ATTEMPTS.
  while (WiFi.status() != WL_CONNECTED && attempts < WIFI_MAX_ATTEMPTS)
  {
    // Check emergency button even during blocking WiFi connect?
    // Difficult without restructuring to be fully non-blocking.
    // For now, accept that emergency might be slightly delayed if pressed *during* WiFi.begin()
    checkEmergencyButton();
    if (emergencyButtonState && !emergencyActive)
      break; // Abort connection attempt if emergency pressed

    delay(WIFI_ATTEMPT_DELAY);
    // Serial.print("."); // Can be noisy
    attempts++;
  }

  // Re-check emergency status after loop in case it was pressed during delay
  checkEmergencyButton();
  if (emergencyButtonState && !emergencyActive)
  {
    log("WIFI", "Emergency detected during WiFi connect attempt. Aborting connection.");
    return; // Don't proceed with connection status check
  }

  if (WiFi.status() == WL_CONNECTED)
  {
    log("WIFI", "Connected!");
    Serial.print("  IP Address: ");
    Serial.println(WiFi.localIP());
  }
  else
  {
    log("ERROR", "WiFi connection FAILED after attempts!");
    // Stay in CONNECTING state, will retry later.
  }
}

void setupMQTT()
{
  // Configure MQTT client settings
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(handleMQTTCallback);
  mqtt.setKeepAlive(60);    // seconds
  mqtt.setSocketTimeout(5); // seconds
}

void handleMQTTCallback(char *topic, byte *payload, unsigned int length)
{
  log("MQTT", "Message received:");
  Serial.print("  Topic: ");
  Serial.println(topic);

  // Null-terminate the payload to treat it as a C-string
  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0'; // Use null terminator
  Serial.print("  Payload: ");
  Serial.println(message);

  // Check if the topic is the Unlock topic
  if (strcmp(topic, TOPIC_UNLOCK) == 0)
  {
    // Check if we are in a state where unlock is allowed (e.g., not already in emergency?)
    // Allowing unlock even in emergency might be desired (e.g., remote override)
    if (currentState != ERROR_STATE)
    {
      log("CONTROL", "Unlock command received via MQTT");
      sendServoTriggerSignal();
    }
    else
    {
      log("WARN", "Unlock command received via MQTT, but system is in ERROR state. Ignoring.");
    }
  }
  else
  {
    log("MQTT", "Received message on unhandled topic");
  }
}

void updateStatusLED()
{
  switch (currentState)
  {
  case CONNECTING:
    // Fast blink while connecting
    digitalWrite(STATUS_LED_PIN, (millis() / 250) % 2);
    break;
  case OPERATIONAL:
    // Slow blink when operational
    digitalWrite(STATUS_LED_PIN, (millis() / 1000) % 2);
    break;
  case EMERGENCY:
    // Solid ON during emergency
    digitalWrite(STATUS_LED_PIN, HIGH);
    break;
  case ERROR_STATE:
    // Solid ON for error
    digitalWrite(STATUS_LED_PIN, HIGH);
    break;
  case INIT: // Should not happen in loop
  default:
    digitalWrite(STATUS_LED_PIN, LOW); // Off otherwise
    break;
  }
}

// Simple logging helper
void log(const char *event, const char *message)
{
  Serial.print("[");
  Serial.print(millis());
  Serial.print("] [");
  Serial.print(event);
  Serial.print("] ");
  Serial.println(message);
}

// Function to generate a random mock RFID string
String getRandomRFID()
{
  return MOCK_RFIDS[random(NUM_MOCK_RFIDS)];
}

// --- Deprecated / Unused ---
// void sendSignalPulse(int pin, unsigned long duration) { ... }
// void checkConnections() { ... } // Logic moved into handleConnectingState