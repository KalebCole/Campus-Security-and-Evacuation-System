#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Base64.h>
#include <Esp.h>
// #include "../src/config.h"  // Removed - Merging directly
// #include "../src/wifi/wifi.h" // Removed - Merging directly
// #include "../src/mqtt/mqtt.h" // Removed - Merging directly
#include <eloquent_esp32cam.h>
#include <eloquent_esp32cam/face/detection.h>
#include <eloquent_esp32cam/camera/pinout.h>

// --- Merged Config ---
// WiFi Configuration
#define WIFI_SSID "iPod Mini"    // Replace with your SSID
#define WIFI_PASSWORD "H0t$p0t!" // Replace with your Password
#define WIFI_TIMEOUT 10000       // 10 seconds timeout
#define WIFI_ATTEMPT_DELAY 500   // 500ms between attempts

// MQTT Configuration
#define MQTT_BROKER "172.20.10.2" // Replace with your MQTT Broker IP or hostname
#define MQTT_PORT 1883
#define MQTT_CLIENT_ID "esp32_cam_test_complete" // Use a unique ID for the test
#define MQTT_BUFFER_SIZE 30000                   // Buffer size for MQTT messages

// MQTT Topics (Only the one used by the test)
#define TOPIC_SESSION "campus/security/session"
#define TOPIC_EMERGENCY "campus/security/emergency" // Keep for callback example

// Camera Pin Definitions (Assuming they are needed/used by Eloquent setup)
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 21
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y2_GPIO_NUM 4
#define Y3_GPIO_NUM 5
#define Y4_GPIO_NUM 18
#define Y5_GPIO_NUM 19
#define Y6_GPIO_NUM 36
#define Y7_GPIO_NUM 39
#define Y8_GPIO_NUM 34
#define Y9_GPIO_NUM 35
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

// --- Merged WiFi ---
bool wifiConnected = false;
unsigned long lastConnectionAttempt = 0;
const unsigned long CONNECTION_RETRY_DELAY = 5000; // 5 seconds between retry attempts

bool connectToWiFi()
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
        wifiConnected = true;
        Serial.println("\nWiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        return true;
    }
    else
    {
        wifiConnected = false;
        Serial.println("\nWiFi connection failed!");
        WiFi.disconnect(true);
        delay(100);
        return false;
    }
}

void setupWifi()
{
    // WiFi.mode(WIFI_STA);
    lastConnectionAttempt = 0; // Force immediate connection attempt
    connectToWiFi();           // Attempt connection directly in setup for test
}

bool isWiFiConnected()
{
    return WiFi.status() == WL_CONNECTED;
}

// --- Merged MQTT ---
WiFiClient espClient;
PubSubClient mqttClient(espClient);
bool mqttConnected = false; // Renamed from isMQTTConnected in original module to avoid conflict

void mqttCallback(char *topic, byte *payload, unsigned int length)
{
    Serial.print("Message arrived [");
    Serial.print(topic);
    Serial.print("] ");
    // Simplified callback for test - just print topic
    Serial.println();
}

bool connectToMQTT()
{
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setBufferSize(MQTT_BUFFER_SIZE); // Set buffer size

    Serial.println("Attempting MQTT connection...");
    if (mqttClient.connect(MQTT_CLIENT_ID))
    {
        mqttConnected = true; // Use the local flag
        Serial.println("MQTT connected");
        mqttClient.subscribe(TOPIC_EMERGENCY); // Example subscription
        return true;
    }
    else
    {
        mqttConnected = false; // Use the local flag
        Serial.print("MQTT connection failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" ");
        return false;
    }
}

void setupMQTT()
{
    connectToMQTT(); // Attempt connection directly in setup for test
}

bool isMQTTConnected() // Keep function name for compatibility with test code
{
    return mqttClient.connected(); // Check client state directly
}

// --- Original Test Code ---

// Use Eloquent objects directly
using eloq::camera;
using eloq::face::detection;

// --- Test Configuration ---
// Goal: Initialize camera, connect WiFi/MQTT, capture one image,
//       run face detection, and publish an complete session payload
//       (image + face detection status + fake rfid tag) to MQTT.

// Global flag to ensure test runs only once
bool testExecuted = false;

// Fake RFID tag
const char *fakeRfidTag = "FAKE123";

void setupCameraForTest()
{
    camera.pinout.aithinker();
    camera.resolution.face();
    detection.accurate();
    detection.confidence(0.7); // Adjust as needed
    camera.pinout.pins.d0 = Y2_GPIO_NUM;
    camera.pinout.pins.d1 = Y3_GPIO_NUM;
    camera.pinout.pins.d2 = Y4_GPIO_NUM;
    camera.pinout.pins.d3 = Y5_GPIO_NUM;
    camera.pinout.pins.d4 = Y6_GPIO_NUM;
    camera.pinout.pins.d5 = Y7_GPIO_NUM;
    camera.pinout.pins.d6 = Y8_GPIO_NUM;
    camera.pinout.pins.d7 = Y9_GPIO_NUM;
    camera.pinout.pins.xclk = XCLK_GPIO_NUM;
    camera.pinout.pins.pclk = PCLK_GPIO_NUM;
    camera.pinout.pins.vsync = VSYNC_GPIO_NUM;
    camera.pinout.pins.href = HREF_GPIO_NUM;
    camera.pinout.pins.sccb_sda = SIOD_GPIO_NUM;
    camera.pinout.pins.sccb_scl = SIOC_GPIO_NUM;
    camera.pinout.pins.pwdn = PWDN_GPIO_NUM;
    camera.pinout.pins.reset = RESET_GPIO_NUM;

    Serial.println("Initializing camera for test...");
    while (!camera.begin().isOk())
    {
        Serial.print("Camera init failed: ");
        Serial.println(camera.exception.toString());
        delay(1000);
    }
    Serial.println("Camera initialized successfully");
}

void runFaceDetectionTest()
{
    if (testExecuted)
        return; // Don't run again

    Serial.println("--- Running Face Detection Test --- ");

    // 1. Ensure WiFi and MQTT are connected
    if (!isWiFiConnected() || !isMQTTConnected())
    {
        Serial.println("WiFi or MQTT not connected. Cannot run test.");
        // Maybe add retry logic here or just wait
        delay(5000);
        return;
    }

    // 2. Capture Image
    Serial.println("Capturing image...");
    if (!camera.capture().isOk())
    {
        Serial.print("Capture failed: ");
        Serial.println(camera.exception.toString());
        return; // Stop test on failure
    }

    // 3. Run Face Detection
    Serial.println("Running face detection...");
    if (!detection.run().isOk())
    {
        Serial.print("Detection failed: ");
        Serial.println(detection.exception.toString());
        return; // Stop test on failure
    }

    bool faceFound = detection.found();
    Serial.print("Face detected: ");
    Serial.println(faceFound ? "Yes" : "No");

    // 4. Prepare Payload
    if (!camera.frame)
    {
        Serial.println("Error: No camera frame buffer available!");
        return;
    }
    uint8_t *imageBuf = camera.frame->buf;
    size_t imageLen = camera.frame->len;

    char *base64Buf = nullptr;
    size_t base64Len = Base64.encodedLength(imageLen);
    base64Buf = (char *)malloc(base64Len + 1);

    if (!base64Buf)
    {
        Serial.println("Failed to allocate memory for Base64 buffer");
        return;
    }
    Base64.encode(base64Buf, (char *)imageBuf, imageLen);
    base64Buf[base64Len] = '\0';

    StaticJsonDocument<25000> jsonDoc; // Adjust size as needed
    char jsonBuffer[25000];

    jsonDoc["device_id"] = MQTT_CLIENT_ID;
    jsonDoc["session_id"] = "test_face_detect_" + String(millis());
    jsonDoc["timestamp"] = millis();
    jsonDoc["session_duration"] = 0;
    jsonDoc["image_size"] = imageLen;
    jsonDoc["image"] = base64Buf; // Include Base64 image
    jsonDoc["face_detected"] = faceFound;
    jsonDoc["rfid_detected"] = true; // Explicitly true for this test
    jsonDoc["rfid_tag"] = fakeRfidTag;

    size_t jsonLen = serializeJson(jsonDoc, jsonBuffer);
    free(base64Buf); // Free buffer after use

    if (jsonLen == 0 || jsonLen >= sizeof(jsonBuffer))
    {
        Serial.println("Failed to serialize JSON or buffer too small.");
        return;
    }

    // 5. Publish via MQTT
    Serial.printf("Publishing face detection test payload (%d bytes) to %s...\n", jsonLen, TOPIC_SESSION);
    if (mqttClient.publish(TOPIC_SESSION, jsonBuffer, jsonLen))
    {
        Serial.println("Payload published successfully.");
    }
    else
    {
        Serial.println("MQTT publish failed!");
    }

    Serial.println("--- Face Detection Test Complete --- ");
    testExecuted = true; // Mark as done
}

void setup()
{
    Serial.begin(115200);
    delay(3000);
    Serial.println("\n--- Unit Test: Face Detection and MQTT Publish ---");

    setupCameraForTest();
    setupWifi(); // Connect to WiFi
    setupMQTT(); // Connect to MQTT Broker

    Serial.println("Setup complete. Running test once...");
    // We run the main test logic here in setup after connections established
    runFaceDetectionTest();
}

void loop()
{
    // Keep MQTT connection alive
    if (isWiFiConnected() && !isMQTTConnected())
    {
        Serial.println("MQTT disconnected, attempting reconnect...");
        setupMQTT();
    }
    if (isMQTTConnected())
    {
        mqttClient.loop();
    }

    // Test runs only once in setup, loop just maintains connection
    delay(500);
}
