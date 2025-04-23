#include <Arduino.h>
// #include <WiFi.h> // Removed
// #include <PubSubClient.h> // Removed
// #include <ArduinoJson.h> // Removed
#include <Base64.h>
#include <Esp.h>
#include <eloquent_esp32cam.h>
// #include <eloquent_esp32cam/face/detection.h> // Removed
#include <eloquent_esp32cam/camera/pinout.h>
// #include "FS.h"     // Removed
// #include "SPIFFS.h" // Removed

// --- Configuration ---
// WiFi Configuration - REMOVED
// MQTT Configuration - REMOVED
// MQTT Topics - REMOVED

// Camera Pin Definitions
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

// Test Specific Definitions - REMOVED
// const char *OUTPUT_FILENAME = "/face_capture.json";
// const unsigned long DETECTION_TIMEOUT_MS = 15000;
// const int DETECTION_LOOP_DELAY_MS = 200;

// --- Global Objects & Variables ---
using eloq::camera;
// using eloq::face::detection; // Removed

// WiFiClient wifiClient; // Removed
// PubSubClient mqttClient(wifiClient); // Removed

// Test Control Flag
// bool imagePrinted = false; // Removed: No longer needed, capture on demand

// --- Forward Declarations ---
void setupCameraForTest();

// --- Removed Network Setup Functions ---
// bool connectToWiFi() { return false; }
// void setupWifi() {}
// bool isWiFiConnected() { return false; }
// void mqttCallback(char *topic, byte *payload, unsigned int length) {}
// bool connectToMQTT() { return false; }
// void setupMQTT() {}
// bool isMQTTConnected() { return false; }

// --- Camera Setup ---
void setupCameraForTest()
{
    camera.pinout.aithinker();
    camera.resolution.face(); // Use a resolution suitable for viewing
    // detection.accurate(); // Removed
    // detection.confidence(0.7); // Removed
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

// --- Removed File Save Function ---
// void saveCaptureToFile(bool faceWasDetected) {}

// --- Main Setup ---
void setup()
{
    Serial.begin(115200);
    delay(3000);
    Serial.println("\n--- Unit Test: Capture and Print Base64 Image ---");

    setupCameraForTest();
    // setupWifi(); // Removed
    // setupMQTT(); // Removed
    // Initialize SPIFFS - Removed

    // imagePrinted = false; // Removed
    Serial.println("Setup complete. Press 'M' in Serial Monitor to capture image.");
}

// --- Main Loop ---
void loop()
{
    // Check for serial input
    if (Serial.available() > 0)
    {
        char incomingChar = Serial.read();

        // Check if the received character is 'M' or 'm'
        if (incomingChar == 'M' || incomingChar == 'm')
        {
            Serial.println("\n--- Capturing image on 'M' press ---");

            // 1. Capture Image
            if (!camera.capture().isOk())
            {
                Serial.print("Capture command failed: ");
                Serial.println(camera.exception.toString());
                return; // Exit this capture attempt
            }

            // 2. Check Frame Validity
            if (!camera.frame || !camera.frame->buf || camera.frame->len == 0)
            {
                Serial.println("ERROR: Captured frame is invalid or zero length.");
                return; // Exit this capture attempt
            }
            Serial.printf("Frame captured successfully (Size: %d bytes).\n", camera.frame->len);

            // 3. Allocate Base64 Buffer
            size_t base64Len = Base64.encodedLength(camera.frame->len);
            Serial.printf("Allocating buffer for Base64 (Size: %d bytes)...\n", base64Len + 1);
            char *base64Buf = (char *)malloc(base64Len + 1);

            if (!base64Buf)
            {
                Serial.println("ERROR: Failed to allocate memory for Base64 buffer");
                return; // Stop if allocation fails
            }
            Serial.println("Buffer allocated.");

            // 4. Encode
            Serial.println("Encoding image to Base64...");
            unsigned long encodeStart = millis();
            Base64.encode(base64Buf, (char *)camera.frame->buf, camera.frame->len);
            base64Buf[base64Len] = '\0'; // Null-terminate
            Serial.printf("Base64 encoding took %lu ms.\n", millis() - encodeStart);

            // 5. Print Base64 String (without trailing newline)
            Serial.println("--- BASE64 START ---");
            Serial.print(base64Buf);                // Use print instead of println
            Serial.println("\n--- BASE64 END ---"); // Add newline before END marker for clarity

            // 6. Cleanup
            free(base64Buf);
            Serial.println("Base64 buffer freed.");
            Serial.println("Ready for next 'M' press.");

            // 7. Set flag to prevent re-running // Removed
            // imagePrinted = true; // Removed
            // Serial.println("Test complete. Image printed to Serial."); // Removed
        }
        // Optional: Handle other characters if needed
        // else {
        //     Serial.printf("Received '%c', ignoring. Press 'M' to capture.\n", incomingChar);
        // }
    }

    // Add a small delay to prevent the loop from running too fast
    delay(50);
}
