#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Base64.h>
#include <Esp.h> // Include for ESP.getFreeHeap()
#include "config.h"
#include <eloquent_esp32cam.h>
#include <eloquent_esp32cam/face/detection.h>
#include <eloquent_esp32cam/camera/pinout.h>
#include "wifi/wifi.h"
#include "mqtt/mqtt.h"
#include "leds/led_control.h"
#include "serial_handler/serial_handler.h"

using eloq::camera;
using eloq::face::detection;

// State machine related variables
StateMachine currentState = IDLE;
unsigned long lastStateChange = 0;
bool faceDetectedInSession = false;

// Session management variables
String currentSessionId = "";
unsigned long sessionStartTime = 0;


void setupCamera()
{
  camera.pinout.aithinker();
  camera.resolution.face();
  detection.accurate();
  detection.confidence(0.7);

  // pins
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

  // Initialize camera
  Serial.println("Initializing camera...");
  while (!camera.begin().isOk())
  {
    Serial.print("Camera init failed: ");
    Serial.println(camera.exception.toString());
    delay(1000);
  }
  Serial.println("Camera initialized successfully");
}

// Generate a random session ID (timestamp + random number)
String generateSessionId()
{
  return "session_" + String(millis()) + "_" + String(random(10000));
}

void setup()
{
  Serial.begin(115200);
  delay(3000); // Give time to open serial monitor

  // Setup hardware components
  setupLEDs();
  setupCamera();
  setupSerialHandler();

  // Initialize random seed
  randomSeed(analogRead(0));

  // Set initial state to IDLE
  currentState = IDLE;
  lastStateChange = millis();
  clearSerialFlags();

  Serial.println("ESP32-CAM System initialized. Waiting for motion detection...");
}

void handleIdleState()
{
  // Wait for motion detection flag from serial_handler
  if (motionDetected)
  {
    Serial.println("Motion detected! Transitioning to CONNECTING state...");
    currentState = CONNECTING;
    lastStateChange = millis();
    setupWifi();
  }
}

void handleConnectingState()
{
  // First check if WiFi is connected
  if (!isWiFiConnected())
  {
    if (millis() - lastStateChange > RETRY_DELAY)
    {
      // Retry WiFi connection after delay
      Serial.println("Connecting to WiFi...");
      setupWifi();
      lastStateChange = millis();
    }
    return;
  }

  // Once WiFi is connected, check MQTT
  if (!isMQTTConnected())
  {
    if (millis() - lastStateChange > RETRY_DELAY / 2)
    {
      // Retry MQTT connection after delay
      Serial.println("WiFi connected. Connecting to MQTT...");
      setupMQTT();
      lastStateChange = millis();
    }
    return;
  }

  // If both are connected, move to face detection
  Serial.println("WiFi and MQTT connected. Transitioning to FACE_DETECTING state...");
  currentState = FACE_DETECTING;
  lastStateChange = millis();
}

void handleFaceDetectingState()
{
  Serial.println("Capturing image and detecting faces...");

  // Capture image
  if (!camera.capture().isOk())
  {
    Serial.print("Capture failed: ");
    Serial.println(camera.exception.toString());
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }

  // Run face detection
  Serial.println("Running face detection...");
  if (!detection.run().isOk())
  {
    Serial.print("Detection failed: ");
    Serial.println(detection.exception.toString());
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }

  faceDetectedInSession = detection.found();
  if (faceDetectedInSession)
  {
    Serial.println("Face detected!");
  }
  else
  {
    Serial.println("No faces detected");
  }

  currentSessionId = generateSessionId();
  sessionStartTime = millis();
  currentState = SESSION;
  lastStateChange = millis();
  Serial.println("Transitioning to SESSION state...");
}

void handleSessionState()
{
  // Wait for RFID data or timeout
  bool rfidTimedOut = false;
  if (!rfidDetected)
  {
    if (millis() - lastStateChange > RFID_WAIT_TIMEOUT_MS)
    {
      Serial.println("RFID wait timeout. Proceeding without RFID tag.");
      rfidTimedOut = true;
    }
    else
    {
      return;
    }
  }

  Serial.println("Creating session payload...");

  if (!camera.frame)
  {
    Serial.println("Error: No camera frame buffer available!");
    currentState = ERROR;
    lastStateChange = millis();
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
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }
  Base64.encode(base64Buf, (char *)imageBuf, imageLen);
  base64Buf[base64Len] = '\0';

  StaticJsonDocument<25000> jsonDoc;
  char jsonBuffer[25000];

  jsonDoc["device_id"] = MQTT_CLIENT_ID;
  jsonDoc["session_id"] = currentSessionId;
  jsonDoc["timestamp"] = millis();
  jsonDoc["session_duration"] = millis() - sessionStartTime;
  jsonDoc["image_size"] = imageLen;
  jsonDoc["image"] = base64Buf;
  jsonDoc["face_detected"] = faceDetectedInSession;

  jsonDoc["rfid_detected"] = rfidDetected;
  if (rfidDetected)
  {
    jsonDoc["rfid_tag"] = rfidTag;
  }

  size_t jsonLen = serializeJson(jsonDoc, jsonBuffer);
  if (jsonLen == 0 || jsonLen >= sizeof(jsonBuffer))
  {
    Serial.println("Failed to serialize JSON payload or buffer too small.");
    free(base64Buf);
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }

  Serial.printf("Publishing payload (%d bytes) to %s...\n", jsonLen, TOPIC_SESSION);
  if (mqttClient.publish(TOPIC_SESSION, jsonBuffer, jsonLen))
  {
    Serial.println("Payload published successfully.");
  }
  else
  {
    Serial.println("MQTT publish failed!");
  }

  free(base64Buf);
  clearSerialFlags();
  currentState = IDLE;
  lastStateChange = millis();
  Serial.println("Session complete. Returning to IDLE state.");
}

void handleEmergencyState()
{
  Serial.println("EMERGENCY state active");
  if (millis() - lastStateChange > EMERGENCY_TIMEOUT)
  {
    Serial.println("Emergency timeout elapsed. Returning to IDLE state.");
    clearSerialFlags();
    currentState = IDLE;
    lastStateChange = millis();
  }
}

void handleErrorState()
{
  Serial.println("ERROR state: Attempting recovery...");
  if (millis() - lastStateChange > RETRY_DELAY)
  {
    Serial.println("Retry delay elapsed. Returning to IDLE state.");
    clearSerialFlags();
    currentState = IDLE;
    lastStateChange = millis();
  }
}

void loop()
{
  updateLEDStatus(currentState);
  
  processSerialData();

  if (emergencyDetected && currentState != EMERGENCY)
  {
    Serial.println("Emergency detected! Transitioning to EMERGENCY state.");
    currentState = EMERGENCY;
    lastStateChange = millis();
  }

  if (currentState != EMERGENCY)
  {
    switch (currentState)
    {
    case IDLE:
      handleIdleState();
      break;
    case CONNECTING:
      handleConnectingState();
      break;
    case FACE_DETECTING:
      handleFaceDetectingState();
      break;
    case SESSION:
      handleSessionState();
      break;
    case ERROR:
      handleErrorState();
      break;
    default:
      currentState = IDLE;
      lastStateChange = millis();
      break;
    }
  }
  else
  {
    handleEmergencyState();
  }

  delay(10);
}