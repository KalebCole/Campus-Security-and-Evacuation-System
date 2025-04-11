#include <Arduino.h>
#include <WiFiS3.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"

// Simple logging helper
void log(const char *event, const char *message)
{
    Serial.print("[");
    Serial.print(millis());
    Serial.print("] ");
    Serial.print(event);
    Serial.print(": ");
    Serial.println(message);
}



// Current state
StateMachine currentState = IDLE;

// Global variables (defined as extern in config.h)
bool isEmergencyMode = false;
unsigned long lastLedToggle = 0;
bool ledState = false;
unsigned long lastRFIDCheck = 0;
unsigned long unlockStartTime = 0;
bool unlockInProgress = false;
unsigned long lastMotionCheck = 0;
bool motionDetected = false;
unsigned long emergencyStartTime = 0;
unsigned long errorStartTime = 0; // Added for error timeout tracking

// Session management
unsigned long sessionStartTime = 0;
const unsigned long SESSION_TIMEOUT = 3000; // 3 seconds timeout for session
bool sessionActive = false;

// MQTT client setup
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

// Function declarations
void handleState();
void connectToServices();
void handleEmergency();
void handleRFID();
void handleUnlock();
void updateLED();
void handleMotion();
void printState(const char *message = nullptr);
void setupCommunication();
void checkConnections();
void handleMQTTCallback(char *topic, byte *payload, unsigned int length);
void runTests();
void sendUnlockSignal();
String getRandomRFID();

// Setup communication with WiFi and MQTT
void setupCommunication()
{
    log("WIFI", "Setting up communication...");

    if (WiFi.status() == WL_NO_MODULE)
    {
        log("ERROR", "Communication with WiFi module failed!");
        currentState = ERROR;
        errorStartTime = millis();
        return;
    }

    log("WIFI", "Connecting to network...");

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < WIFI_MAX_ATTEMPTS)
    {
        delay(WIFI_ATTEMPT_DELAY);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() != WL_CONNECTED)
    {
        log("ERROR", "WiFi connection failed!");
        currentState = ERROR;
        errorStartTime = millis();
        return;
    }

    log("WIFI", "Connected successfully!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    // Setup MQTT with improved settings
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(handleMQTTCallback);
    mqtt.setKeepAlive(60);    // Set keepalive to 60 seconds
    mqtt.setSocketTimeout(5); // Set socket timeout to 5 seconds

    log("MQTT", "Connecting to broker...");
    if (mqtt.connect(MQTT_CLIENT_ID))
    {
        log("MQTT", "Connected successfully!");
        mqtt.subscribe(TOPIC_UNLOCK);
    }
    else
    {
        log("ERROR", "MQTT connection failed!");
        currentState = ERROR;
        errorStartTime = millis();
    }
}

void setup()
{
    Serial.begin(115200);
    // Add timeout for Serial initialization
    unsigned long startTime = millis();
    while (!Serial && millis() - startTime < 3000)
    {
        ; // Wait up to 3 seconds for serial port
    }
    log("INIT", "System starting...");

    // Configure pins
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(MOTION_PIN, INPUT); // Motion sensor
    pinMode(EMERGENCY_PIN, INPUT);
    pinMode(RFID_PIN, INPUT);
    pinMode(UNLOCK_PIN, OUTPUT);
    digitalWrite(UNLOCK_PIN, LOW);

    log("INIT", "Pins configured");

    // Initialize random seed for mock RFID
    randomSeed(analogRead(0));

    // Run startup tests
    runTests();

    setupCommunication();
}

void loop()
{
    static unsigned long lastLog = 0;
    // Log state every 5 seconds to avoid flooding serial
    if (millis() - lastLog > 5000)
    {
        log("STATE", currentState == IDLE ? "IDLE" : currentState == ACTIVE_WAITING ? "WAITING"
                                                 : currentState == ACTIVE_SESSION   ? "SESSION"
                                                 : currentState == EMERGENCY        ? "EMERGENCY"
                                                                                    : "ERROR");
        lastLog = millis();
    }

    handleState();
    delay(10);
}

void handleState()
{
    // Handle motion detection
    handleMotion();

    // Print state changes
    static StateMachine lastState = currentState;
    if (lastState != currentState)
    {
        printState();
        lastState = currentState;
    }

    // Check emergency in any state
    if (digitalRead(EMERGENCY_PIN) == HIGH)
    {
        currentState = EMERGENCY;
        handleEmergency();
        return;
    }

    // Check error timeout
    if (currentState == ERROR && millis() - errorStartTime >= ERROR_TIMEOUT_MS)
    {
        log("STATE", "Error timeout reached, returning to IDLE");
        currentState = IDLE;
        return;
    }

    // Main state handling
    switch (currentState)
    {
    case IDLE:
        // In IDLE, just wait for motion
        digitalWrite(LED_BUILTIN, LOW);
        break;

    case ACTIVE_WAITING:
        // Check connections
        if (!mqtt.connected() || WiFi.status() != WL_CONNECTED)
        {
            connectToServices();
            break;
        }

        // Process MQTT messages
        mqtt.loop();

        // Check for RFID if not in emergency
        if (!isEmergencyMode)
        {
            int rfidState = digitalRead(RFID_PIN);
            Serial.print("RFID Pin State: ");
            Serial.println(rfidState);

            if (rfidState == LOW && millis() - lastRFIDCheck >= RFID_DEBOUNCE_TIME)
            {
                Serial.println("RFID Detected! Starting new session...");
                handleRFID();
                sessionStartTime = millis();
                sessionActive = true;
                currentState = ACTIVE_SESSION;
                lastRFIDCheck = millis();
            }
        }

        handleUnlock();
        break;

    case ACTIVE_SESSION:
        // Process MQTT messages
        mqtt.loop();

        // Check session timeout
        if (millis() - sessionStartTime >= SESSION_TIMEOUT)
        {
            Serial.println("Session timeout, returning to IDLE");
            sessionActive = false;
            currentState = IDLE;
        }

        // Ignore new RFID reads during active session
        if (digitalRead(RFID_PIN) == LOW)
        {
            Serial.println("RFID detected but ignored - session in progress");
        }

        handleUnlock();
        break;

    case EMERGENCY:
        handleUnlock();
        break;

    case ERROR:
        // Fast error blink
        if (millis() - lastLedToggle >= LED_ERROR_BLINK)
        {
            ledState = !ledState;
            digitalWrite(LED_BUILTIN, ledState);
            lastLedToggle = millis();
        }
        break;
    }

    updateLED();
}

void connectToServices()
{
    // Connect WiFi if needed
    if (WiFi.status() != WL_CONNECTED)
    {
        Serial.print("Connecting WiFi...");
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < WIFI_MAX_ATTEMPTS)
        {
            delay(WIFI_ATTEMPT_DELAY);
            Serial.print(".");
            attempts++;
        }

        if (WiFi.status() != WL_CONNECTED)
        {
            currentState = ERROR;
            return;
        }
        Serial.println("\nWiFi connected!");
    }

    // Connect MQTT if needed
    if (!mqtt.connected())
    {
        Serial.println("Connecting MQTT...");
        mqtt.setServer(MQTT_BROKER, MQTT_PORT);
        mqtt.setCallback(handleMQTTCallback);

        if (mqtt.connect(MQTT_CLIENT_ID))
        {
            mqtt.subscribe(TOPIC_UNLOCK);
            Serial.println("MQTT connected!");
        }
        else
        {
            currentState = ERROR;
        }
    }
}

void handleUnlock()
{
    if (unlockInProgress && (millis() - unlockStartTime >= UNLOCK_SIGNAL_DURATION))
    {
        digitalWrite(UNLOCK_PIN, LOW);
        unlockInProgress = false;
        Serial.println("Unlock completed");
    }
}

void updateLED()
{
    switch (currentState)
    {
    case IDLE:
        digitalWrite(LED_BUILTIN, LOW);
        break;

    case ACTIVE_WAITING:
        if (millis() - lastLedToggle >= LED_NORMAL_BLINK)
        {
            ledState = !ledState;
            digitalWrite(LED_BUILTIN, ledState);
            lastLedToggle = millis();
        }
        break;

    case ACTIVE_SESSION:
        if (millis() - lastLedToggle >= (LED_NORMAL_BLINK / 2))
        { // Faster blink during session
            ledState = !ledState;
            digitalWrite(LED_BUILTIN, ledState);
            lastLedToggle = millis();
        }
        break;

    case EMERGENCY:
        digitalWrite(LED_BUILTIN, HIGH);
        break;

    case ERROR:
        if (millis() - lastLedToggle >= 200)
        {
            ledState = !ledState;
            digitalWrite(LED_BUILTIN, ledState);
            lastLedToggle = millis();
        }
        break;
    }
}

void handleEmergency()
{
    if (!isEmergencyMode)
    {
        isEmergencyMode = true;
        log("EMERGENCY", "Emergency mode activated!");
        sendUnlockSignal();

        StaticJsonDocument<200> doc;
        doc["device_id"] = MQTT_CLIENT_ID;
        doc["event"] = "emergency";
        doc["action"] = "unlock_triggered";
        doc["timestamp"] = millis();

        char buffer[200];
        serializeJson(doc, buffer);

        mqtt.publish(TOPIC_EMERGENCY, buffer);
    }
}

void handleRFID()
{
    // Read the actual RFID input pin
    int rfidState = digitalRead(RFID_PIN);

    if (rfidState == LOW && millis() - lastRFIDCheck >= RFID_DEBOUNCE_TIME)
    {
        // Generate a mock RFID value when the pin is triggered
        String rfid = getRandomRFID();
        log("RFID", rfid.c_str());

        StaticJsonDocument<200> doc;
        doc["device_id"] = MQTT_CLIENT_ID;
        doc["rfid"] = rfid;
        doc["timestamp"] = millis();

        char buffer[200];
        serializeJson(doc, buffer);

        log("MQTT", buffer);

        if (mqtt.publish(TOPIC_RFID, buffer))
        {
            log("MQTT", "Message published successfully!");
        }
        else
        {
            log("ERROR", "Failed to publish MQTT message!");
        }

        // Visual feedback
        digitalWrite(LED_BUILTIN, HIGH);
        delay(LED_RFID_BLINK);
        digitalWrite(LED_BUILTIN, LOW);

        lastRFIDCheck = millis();
    }
}

void sendUnlockSignal()
{
    if (!unlockInProgress)
    {
        digitalWrite(UNLOCK_PIN, HIGH);
        unlockStartTime = millis();
        unlockInProgress = true;
        log("UNLOCK", "Door unlock triggered");
    }
}

void handleMotion()
{
    if (millis() - lastMotionCheck >= MOTION_DEBOUNCE)
    {
        int motionState = digitalRead(MOTION_PIN);

        if (currentState == IDLE && motionState == HIGH)
        {
            motionDetected = true;
            currentState = ACTIVE_WAITING;
            log("MOTION", "Detected - Activating");
        }
        else if (currentState == ACTIVE_WAITING && motionState == LOW)
        {
            motionDetected = false;
            currentState = IDLE;
            log("MOTION", "Cleared - Going idle");
        }
        lastMotionCheck = millis();
    }
}

void printState(const char *message)
{
    Serial.println("================================================");
    Serial.print("Current State: ");
    switch (currentState)
    {
    case IDLE:
        Serial.println("IDLE");
        break;
    case ACTIVE_WAITING:
        Serial.println("ACTIVE_WAITING");
        break;
    case ACTIVE_SESSION:
        Serial.println("ACTIVE_SESSION");
        break;
    case EMERGENCY:
        Serial.println("EMERGENCY");
        break;
    case ERROR:
        Serial.println("ERROR");
        break;
    }
    if (message)
    {
        Serial.println(message);
    }
    Serial.println("================================================");
}

// MQTT message callback
void handleMQTTCallback(char *topic, byte *payload, unsigned int length)
{
    // Convert payload to string
    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';

    Serial.print("Message received on topic: ");
    Serial.println(topic);
    Serial.print("Message: ");
    Serial.println(message);
}

// Test function to verify functionality
void runTests()
{
    Serial.println("\n=== Starting Tests ===");

    // Test 1: WiFi Connection
    Serial.println("\nTest 1: WiFi Connection");
    setupCommunication();
    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println("✓ WiFi Test PASSED");
    }
    else
    {
        Serial.println("✗ WiFi Test FAILED");
    }

    // Test 2: MQTT Connection
    Serial.println("\nTest 2: MQTT Connection");
    if (mqtt.connected())
    {
        Serial.println("✓ MQTT Test PASSED");

        // Test 2.1: MQTT Publish
        Serial.println("Testing MQTT Publish...");
        if (mqtt.publish("campus/security/rfid", "1234567890"))
        {
            Serial.println("✓ MQTT Publish Test PASSED");
        }
        else
        {
            Serial.println("✗ MQTT Publish Test FAILED");
        }
    }
    else
    {
        Serial.println("✗ MQTT Test FAILED");
    }

    // Test 3: State Machine
    Serial.println("\nTest 3: State Machine");
    Serial.println("Simulating motion detection cycle...");
    Serial.println("Watch LED patterns:");
    Serial.println("- IDLE: LED off");
    Serial.println("- ACTIVE: LED blinking");
    Serial.println("- Will cycle every 10 seconds");

    Serial.println("\n=== Tests Complete ===\n");
}

String getRandomRFID()
{
    return MOCK_RFIDS[random(NUM_MOCK_RFIDS)];
}
