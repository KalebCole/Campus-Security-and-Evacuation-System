#include <Arduino.h>
#include <WiFiS3.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Constants
const bool RFID_MOCK = true;       // Set to true to use mock RFID database
const int RFID_PIN = 2;            // RFID reader pins

// MQTT Configuration
const char* MQTT_BROKER = "172.20.10.2";  // Use ip of mobile hotspot
const int MQTT_PORT = 1883;             // MQTT broker port
const char* MQTT_CLIENT_ID = "arduino_uno_r4";  // Unique client ID

// MQTT Topics
const char* TOPIC_STATUS = "campus/security/status";
const char* TOPIC_RFID = "campus/security/rfid";
const char* TOPIC_AUTH = "campus/security/auth";
const char* TOPIC_SESSION = "campus/security/session";

// System activity constants
bool systemActive = false;         // System activation status
const int ACTIVATION_DELAY = 2000; // Wait 2 seconds after activation before sending RFID

// WiFi debugging constants
const bool WIFI_DEBUG = true;          // Enable detailed WiFi debugging
const int WIFI_CHECK_INTERVAL = 30000; // Check WiFi status every 30 seconds
const int MAX_WIFI_RETRIES = 5;        // Maximum number of reconnection attempts
unsigned long lastWifiCheck = 0;       // Last time WiFi status was checked

// LED blink patterns
const int WIFI_CONNECTING_BLINK = 100; // Fast blink while connecting
const int WIFI_CONNECTED_BLINK = 2000; // Slow blink when connected
const int WIFI_ERROR_BLINK = 300;      // Medium fast blink on error
const int MQTT_CONNECTING_BLINK = 150; // Medium blink while connecting to MQTT
const int MQTT_CONNECTED_BLINK = 2500; // Very slow blink when MQTT connected

// WIFI Constants for Kaleb's Mobile Hotspot
const char *ssid = "iPod Mini";
const char *password = "H0t$p0t!";

// Create MQTT client
WiFiClient mqttClient;
PubSubClient mqtt(mqttClient);

// Current session ID for RFID processs
String currentSessionId = "";

// RFID database (mock)
const String RFID_DATABASE[] = {
    "123456", // Bob
    "654321", // Rob
    "789012"  // Charlie
};

// sizeof(RFID_DATABASE) gives you the total size in bytes of the entire array
// sizeof(RFID_DATABASE[0]) gives you the size in bytes of a single element
// Dividing the total size by the size of one element gives you the number of elements
const int NUM_RFIDS = sizeof(RFID_DATABASE) / sizeof(RFID_DATABASE[0]);

// State machine constants
const int WIFI_TIMEOUT = 30000;    // 30 seconds to connect to WiFi
const int ERROR_COOLDOWN = 5000;   // 5 seconds in error state
const int STATE_TIMEOUT = 10000;   // 10 seconds timeout for any state
const int MQTT_TIMEOUT = 10000;    // 10 seconds to connect to MQTT

// Process States
enum ProcessState {
  CONNECTING_WIFI,    // Initial state for WiFi connection
  CONNECTING_MQTT,    // Connecting to MQTT broker
  IDLE,               // System is idle after connections
  CHECKING_SYSTEM,    // Checking if system is active
  REQUESTING_SESSION, // Requesting a session ID
  SESSION_READY,      // Session is ready, waiting for RFID
  WAITING_FOR_RFID,   // Waiting for RFID trigger
  SENDING_RFID,       // Sending RFID data
  COOLDOWN,           // Cooldown period between RFID cycles
  ERROR_STATE         // Error state for handling failures
};

// Current state in the RFID process
ProcessState currentState = CONNECTING_WIFI;

// Timing variables
unsigned long stateStartTime = 0;
const int COOLDOWN_PERIOD = 5000; // 5 seconds between complete cycles

// Session management
bool sessionValid = false;
const int SESSION_RETRY_INTERVAL = 10000; // 10 seconds between session retries
unsigned long lastSessionRequestTime = 0;

// Logging constants
const char* LOG_SEPARATOR = "==========================================";
const char* STATE_SEPARATOR = "------------------------------------------";
const char* ERROR_SEPARATOR = "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";

// Function Prototypes
void logState(const char* message, bool isError);
void printWifiStatus();
void connectToWifi();
void checkWifiStatus();
void blinkLED(int blinkRate, int numBlinks);
void wifiStatusLED();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void connectToMqtt();
void checkMqttConnection();
void publishMqttMessage(const char* topic, const char* message);
void subscribeToMqttTopics();
String getRandomRFID();
void triggerRFID(int pinNumber);
bool checkSystemStatus();
bool activateSystem();
bool requestSessionId();
bool hasValidSession();
void resetProcessState();
void executeStateMachine();

// Add logging helper function
void logState(const char* message, bool isError) {
  Serial.println();
  if (isError) {
    Serial.println(ERROR_SEPARATOR);
    Serial.print("ERROR: ");
  } else {
    Serial.println(STATE_SEPARATOR);
  }
  Serial.print("Time: ");
  Serial.print(millis());
  Serial.print(" | State: ");
  Serial.print(currentState);
  Serial.print(" | ");
  Serial.println(message);
  if (isError) {
    Serial.println(ERROR_SEPARATOR);
  } else {
    Serial.println(STATE_SEPARATOR);
  }
  Serial.println();
}

// ----------------
// Function Prototypes
// ----------------

// WIFI
void printWifiStatus();
void connectToWifi();
void checkWifiStatus();
void blinkLED(int blinkRate, int numBlinks);
void wifiStatusLED();

// MQTT
void mqttCallback(char* topic, byte* payload, unsigned int length);
void connectToMqtt();
void checkMqttConnection();
void publishMqttMessage(const char* topic, const char* message);
void subscribeToMqttTopics();

// RFID
String getRandomRFID();
void triggerRFID(int pinNumber);

// System
bool checkSystemStatus();
bool activateSystem();

// Session
bool requestSessionId();
bool hasValidSession();

// State Machine
void resetProcessState();
void executeStateMachine();

// Function to print detailed WiFi status information
void printWifiStatus()
{
  // Print basic WiFi information
  Serial.println("\n----- WiFi Status -----");

  // Connection status
  Serial.print("Status: ");
  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("CONNECTED");
  }
  else
  {
    Serial.println("NOT CONNECTED");
  }

  // Print network info if connected
  if (WiFi.status() == WL_CONNECTED)
  {
    // SSID name
    Serial.print("SSID: ");
    Serial.println(WiFi.SSID());

    // IP address
    IPAddress ip = WiFi.localIP();
    Serial.print("IP: ");
    Serial.println(ip);

    // Signal strength
    Serial.print("Signal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  }

  Serial.println("---------------------");
}

// Function to connect to WiFi with improved error handling and debugging
void connectToWifi()
{
  if (WiFi.status() == WL_NO_MODULE) {
    logState("WiFi module not present!", true);
    while (true); // Don't continue
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.print("Connecting to WiFi network: ");
    Serial.println(ssid);
    
  WiFi.begin(ssid, password);

    // Wait for connection with timeout
    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && 
           millis() - startAttemptTime < WIFI_TIMEOUT) {
      blinkLED(WIFI_CONNECTING_BLINK, 1);
      delay(100);
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      logState("WiFi connected successfully", false);
      printWifiStatus();
    } else {
      logState("WiFi connection failed", true);
    }
  }
}

// Function to periodically check WiFi status
void checkWifiStatus()
{
  if (millis() - lastWifiCheck >= WIFI_CHECK_INTERVAL) {
    if (WiFi.status() != WL_CONNECTED) {
      logState("WiFi connection lost, attempting reconnect...", true);
      connectToWifi();
    }
    lastWifiCheck = millis();
  }
}

// Function to blink LED at a specific rate and number of times
void blinkLED(int blinkRate, int numBlinks)
{
  for (int i = 0; i < numBlinks; i++)
  {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(blinkRate / 2);
    digitalWrite(LED_BUILTIN, LOW);
    delay(blinkRate / 2);
  }
}

// Function to visually indicate WiFi status with LED
void wifiStatusLED()
{
  switch (WiFi.status())
  {
  case WL_CONNECTED:
    // Connected - one long blink
    digitalWrite(LED_BUILTIN, HIGH);
    delay(200);
    digitalWrite(LED_BUILTIN, LOW);
    break;
  case WL_DISCONNECTED:
  case WL_CONNECTION_LOST:
    // Disconnected - two fast blinks
    for (int i = 0; i < 2; i++)
    {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(100);
      digitalWrite(LED_BUILTIN, LOW);
      delay(100);
    }
    break;
  default:
    // Other states - three very fast blinks
    for (int i = 0; i < 3; i++)
    {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(50);
      digitalWrite(LED_BUILTIN, LOW);
      delay(50);
    }
    break;
  }
}

/*

  RFID FUNCTIONS

*/

String getRandomRFID() {
  if (RFID_MOCK) {
    int index = random(NUM_RFIDS);
    return RFID_DATABASE[index];
  }
  return "123456"; // In real mode, this would read from the RFID reader
}

// Store the most recently read RFID value
String currentRFID = "";

// Function to handle RFID detection when we receive a pin on high
void triggerRFID(int pinNumber) {
  String rfid = getRandomRFID();
  if (rfid.length() > 0) {
    StaticJsonDocument<200> doc;
    doc["session_id"] = currentSessionId;
    doc["rfid"] = rfid;
    doc["timestamp"] = millis();
    
    String message;
    serializeJson(doc, message);
    publishMqttMessage(TOPIC_RFID, message.c_str());
  }
}


// Function to request a session ID from the server
bool requestSessionId() {
  if (millis() - lastSessionRequestTime < SESSION_RETRY_INTERVAL) {
    return false;
  }
  
  StaticJsonDocument<200> doc;
  doc["device_id"] = MQTT_CLIENT_ID;
  doc["action"] = "request_session";
  
  String message;
  serializeJson(doc, message);
  publishMqttMessage(TOPIC_SESSION, message.c_str());
  
  lastSessionRequestTime = millis();
  return true;
}

// Check if we have a valid session
bool hasValidSession() {
  return sessionValid && currentSessionId.length() > 0;
}

// Reset the process state machine
void resetProcessState()
{
  currentState = CONNECTING_WIFI;
  stateStartTime = millis();
  sessionValid = false;
  currentSessionId = "";
}

// Execute one step of the state machine
void executeStateMachine()
{
  unsigned long currentTime = millis();
  
  switch (currentState) {
     case CONNECTING_WIFI:
      // Attempt WiFi connection
      if (WiFi.status() != WL_CONNECTED) {
        connectToWifi();
      } else {
        currentState = CONNECTING_MQTT;
        stateStartTime = currentTime;
      }
      break;

    case CONNECTING_MQTT:
      // Attempt MQTT connection
      if (!mqtt.connected()) {
        connectToMqtt();
      } else {
        currentState = IDLE;
        stateStartTime = currentTime;
      }
      break;

  case IDLE:
      // Maintain MQTT connection and check for timeout
      checkMqttConnection();
      if (currentTime - stateStartTime > STATE_TIMEOUT) {
      currentState = CHECKING_SYSTEM;
        stateStartTime = currentTime;
    }
    break;

  case CHECKING_SYSTEM:
      // Check system status and transition accordingly
      if (checkSystemStatus()) {
          currentState = REQUESTING_SESSION;
      } else {
        currentState = IDLE;
      }
      stateStartTime = currentTime;
    break;

  case REQUESTING_SESSION:
      // Request new session and handle response
      if (requestSessionId()) {
      currentState = SESSION_READY;
      } else {
        currentState = ERROR_STATE;
      }
      stateStartTime = currentTime;
    break;

  case SESSION_READY:
      // Verify session validity
      if (hasValidSession()) {
        currentState = WAITING_FOR_RFID;
      } else {
        currentState = ERROR_STATE;
      }
      stateStartTime = currentTime;
      break;

    case WAITING_FOR_RFID:
      // Monitor RFID input
      if (digitalRead(RFID_PIN) == LOW) {
      currentState = SENDING_RFID;
      }
      // Return to idle if timeout occurs
      if (currentTime - stateStartTime > STATE_TIMEOUT) {
        currentState = IDLE;
    }
    break;

  case SENDING_RFID:
      // Send RFID data via MQTT
      triggerRFID(RFID_PIN);
    currentState = COOLDOWN;
      stateStartTime = currentTime;
    break;

  case COOLDOWN:
      // Wait for cooldown period
      if (currentTime - stateStartTime > COOLDOWN_PERIOD) {
      currentState = IDLE;
    }
    break;

    case ERROR_STATE:
      // Handle error state with cooldown
      if (currentTime - stateStartTime > ERROR_COOLDOWN) {
        currentState = CONNECTING_WIFI;
      }
      break;
  }
}

/*

  SYSTEM FUNCTIONS

*/

// Function to check if the system is active
bool checkSystemStatus() {
  StaticJsonDocument<200> doc;
  doc["device_id"] = MQTT_CLIENT_ID;
  doc["action"] = "status_check";
  
  String message;
  serializeJson(doc, message);
  publishMqttMessage(TOPIC_STATUS, message.c_str());
  
  return true;
}

// Function to activate the system
bool activateSystem() {
  StaticJsonDocument<200> doc;
  doc["device_id"] = MQTT_CLIENT_ID;
  doc["command"] = "activate";
  doc["timestamp"] = millis();
  
  String message;
  serializeJson(doc, message);
  publishMqttMessage(TOPIC_STATUS, message.c_str());
  
  // Wait for response (handled in callback)
  return systemActive;
}

// MQTT Callback function
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("Message received on topic: ");
  Serial.println(topic);
  Serial.print("Message: ");
  Serial.println(message);

  // Parse JSON payload
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    logState("Failed to parse JSON message", true);
    return;
  }

  // Handle different topics
  String topicStr = String(topic);
  
  if (topicStr == TOPIC_AUTH) {
    String status = doc["status"];
    if (status == "authenticated") {
      systemActive = true;
    }
  } else if (topicStr == TOPIC_SESSION) {
    String sessionId = doc["session_id"];
    if (sessionId) {
      currentSessionId = sessionId;
      sessionValid = true;
    }
  }
}

// Connect to MQTT broker
void connectToMqtt() {
  if (!mqtt.connected()) {
    logState("Connecting to MQTT broker...", false);
    
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(mqttCallback);
    mqtt.setKeepAlive(60);  // Set keep alive to 60 seconds
    
    if (mqtt.connect(MQTT_CLIENT_ID)) {
      logState("Connected to MQTT broker", false);
      subscribeToMqttTopics();
    } else {
      logState("Failed to connect to MQTT broker", true);
      Serial.print("MQTT connection failed, rc=");
      Serial.println(mqtt.state());
    }
  }
}

// Check MQTT connection status
void checkMqttConnection() {
  if (!mqtt.connected()) {
    logState("MQTT connection lost, attempting reconnect...", true);
    connectToMqtt();
  }
  mqtt.loop();
}

// Publish MQTT message
void publishMqttMessage(const char* topic, const char* message) {
  if (mqtt.connected()) {
    mqtt.publish(topic, message);
    Serial.print("Published to topic: ");
    Serial.println(topic);
    Serial.print("Message: ");
    Serial.println(message);
  } else {
    logState("Cannot publish - MQTT not connected", true);
  }
}

// Subscribe to MQTT topics
void subscribeToMqttTopics() {
  mqtt.subscribe(TOPIC_AUTH);
  mqtt.subscribe(TOPIC_STATUS);
  mqtt.subscribe(TOPIC_SESSION);
}

// ----------------
// Main Setup and Loop
// ----------------

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for serial port to connect
  }

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(RFID_PIN, INPUT_PULLUP);

  // Initialize random seed for mock RFID
  randomSeed(analogRead(0));

  // Initialize state machine
  resetProcessState();
}

void loop() {
  executeStateMachine();
  delay(100);
}