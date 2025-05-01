#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Base64.h>
#include <Esp.h>
#include "config.h"
#include <eloquent_esp32cam.h>
#include <eloquent_esp32cam/camera/pinout.h>
#include <eloquent_esp32cam/face/detection.h>
#include "wifi/wifi.h"
#include "mqtt/mqtt.h"
#include "leds/led_control.h"
#include <esp_random.h>
// #include "serial_handler/serial_handler.h" // Removed for GPIO approach

using eloq::camera;
using eloq::face::detection;

// State machine related variables
StateMachine currentState = IDLE;
unsigned long lastStateChange = 0;
bool faceDetectedInSession = false;

// GPIO Input Pins (Using defines from config.h)
// const int MOTION_INPUT_PIN_MAIN = 18;
// const int RFID_INPUT_PIN_MAIN = 19;

// --- Flags & Data (Defined here, declared extern in config.h) ---
bool motionDetected = false;
bool rfidDetected = false;

const char *FAKE_RFID_TAG_MAIN = "EMP022"; // Hardcoded tag for GPIO approach

// Session management variables
String currentSessionId = "";
unsigned long sessionStartTime = 0;

// Constants for Face Detection Loop
// const unsigned long FACE_DETECTION_TIMEOUT_MS = 10000;
const int FACE_DETECTION_LOOP_DELAY_MS = 200; // Delay between capture attempts

/**
 * Clear GPIO input event flags and RFID tag buffer
 */
void clearInputFlags()
{
  motionDetected = false;
  rfidDetected = false;
  // memset(rfidTag, 0, sizeof(rfidTag)); // Removed - No buffer to clear
}

void setupCamera()
{
  camera.pinout.aithinker();
  camera.brownout.disable();
  // face detection only works at 240x240
  camera.resolution.face();
  camera.quality.high();
  detection.accurate();
  detection.confidence(0.7);

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

  Serial.println("Initializing camera...");
  while (!camera.begin().isOk())
  {
    Serial.print("Camera init failed: ");
    Serial.println(camera.exception.toString());
    delay(1000);
  }
  Serial.println("Camera initialized successfully");
}

String generateSessionId()
{
  char uuid[37];
  uint8_t random_bytes[16];

  for (int i = 0; i < 16; i++)
  {
    random_bytes[i] = esp_random() & 0xFF;
  }

  random_bytes[6] = (random_bytes[6] & 0x0F) | 0x40; // Version 4
  random_bytes[8] = (random_bytes[8] & 0x3F) | 0x80; // Variant 1

  sprintf(uuid, "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
          random_bytes[0], random_bytes[1], random_bytes[2], random_bytes[3],
          random_bytes[4], random_bytes[5],
          random_bytes[6], random_bytes[7],
          random_bytes[8], random_bytes[9],
          random_bytes[10], random_bytes[11], random_bytes[12], random_bytes[13], random_bytes[14], random_bytes[15]);

  return String(uuid);
}

void setup()
{
  Serial.begin(115200);
  delay(3000);

  setupLEDs();
  // setupCamera(); // Called later in handleFaceDetectingState or setup

  // TODO: why is this pullup still floating?
  pinMode(RFID_INPUT_PIN, INPUT);

  randomSeed(analogRead(0));

  currentState = IDLE;
  lastStateChange = millis();
  clearInputFlags();

  Serial.print("Free heap: ");
  Serial.println(ESP.getFreeHeap());
  Serial.println("==========");

  Serial.print("PSRAM: ");
  Serial.println(psramFound() ? "Yes" : "No");
  Serial.println("==========");

  // Initialize Camera ONCE here
  setupCamera();

  Serial.println("ESP32-CAM System initialized. Waiting for motion detection...");
}

void handleIdleState()
{
  // --- DEBUG LOG ---
  Serial.print("[State: IDLE] RFID Pin: ");
  Serial.print(digitalRead(RFID_INPUT_PIN));
  Serial.print(" | rfidDetected Flag: ");
  Serial.println(rfidDetected);
  // --- END DEBUG LOG ---

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
  // --- DEBUG LOG ---
  Serial.print("[State: CONNECTING] RFID Pin: ");
  Serial.print(digitalRead(RFID_INPUT_PIN));
  Serial.print(" | rfidDetected Flag: ");
  Serial.println(rfidDetected);
  // --- END DEBUG LOG ---

  if (!isWiFiConnected())
  {
    if (millis() - lastStateChange > RETRY_DELAY)
    {
      Serial.println("Connecting to WiFi...");
      setupWifi();
      lastStateChange = millis();
    }
    return;
  }

  if (!isMQTTConnected())
  {
    if (millis() - lastStateChange > RETRY_DELAY / 2)
    {
      Serial.println("WiFi connected. Connecting to MQTT...");
      setupMQTT();
      lastStateChange = millis();
    }
    return;
  }

  Serial.println("WiFi and MQTT connected. Transitioning to FACE_DETECTING state...");
  currentState = IMAGE_CAPTURE;
  lastStateChange = millis();
}

void handleImageCaptureState()
{
  // --- DEBUG LOG ---
  Serial.print("[State: IMAGE_CAPTURE Start] RFID Pin: ");
  Serial.print(digitalRead(RFID_INPUT_PIN));
  Serial.print(" | rfidDetected Flag: ");
  Serial.println(rfidDetected);
  // --- END DEBUG LOG ---
  Serial.println("Entering face detection loop...");
  unsigned long startTime = millis();
  faceDetectedInSession = false;
  bool validFrameCaptured = false;

  while (millis() - startTime < FACE_DETECTION_TIMEOUT)
  {
    Serial.printf("Attempting capture & detect cycle (Elapsed: %lu ms)...\n", millis() - startTime);

    if (!camera.capture().isOk())
    {
      Serial.print("Capture command failed: ");
      Serial.println(camera.exception.toString());
      delay(FACE_DETECTION_LOOP_DELAY_MS);
      continue;
    }

    if (!camera.frame)
    {
      Serial.println("WARN: Capture OK, but frame buffer is NULL.");
      delay(FACE_DETECTION_LOOP_DELAY_MS);
      continue;
    }

    if (camera.frame->len == 0)
    {
      Serial.println("WARN: Captured frame has zero length.");
      delay(FACE_DETECTION_LOOP_DELAY_MS);
      continue;
    }

    validFrameCaptured = true;
    Serial.printf("  Valid frame captured (size: %d bytes).\n", camera.frame->len);

    Serial.println("  Running face detection...");
    if (!detection.run().isOk())
    {
      Serial.print("  WARN: Face detection failed: ");
      Serial.println(detection.exception.toString());
    }

    if (detection.found())
    {
      Serial.println("  --> Face detected!");
      faceDetectedInSession = true;
      break;
    }
    else
    {
      Serial.println("  No face detected in this frame.");
    }

    bool currentRfidPinState = (digitalRead(RFID_INPUT_PIN) == HIGH);
    if (currentRfidPinState)
    {
      Serial.println("  (RFID detected during image capture loop)");
      rfidDetected = true;
    }

    delay(FACE_DETECTION_LOOP_DELAY_MS);
  }

  if (!validFrameCaptured)
  {
    Serial.println("ERROR: Failed to capture any valid frame during detection period.");
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }

  if (!faceDetectedInSession)
  {
    Serial.println("Face detection timeout occurred, using last captured frame.");
  }

  Serial.println("Proceeding to session state.");
  currentSessionId = generateSessionId();
  sessionStartTime = millis();
  currentState = SESSION;
  lastStateChange = millis();
  Serial.println("Transitioning to SESSION state...");
}

void handleSessionState()
{
  // --- DEBUG LOG ---
  Serial.print("[State: SESSION Start] RFID Pin: ");
  Serial.print(digitalRead(RFID_INPUT_PIN));
  Serial.print(" | rfidDetected Flag: ");
  Serial.println(rfidDetected);
  // --- END DEBUG LOG ---
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
  delay(1); // Add delay after encoding
  Serial.printf("Image Size (bytes): %d\n", imageLen);
  Serial.printf("Base64 Size (bytes): %d\n", base64Len);
  delay(1);                                // Add delay after encoding
  Serial.print("Free heap before JSON: "); // Check heap BEFORE JSON doc/buffer
  Serial.println(ESP.getFreeHeap());

  // --- Dynamic JSON Allocation ---
  const size_t JSON_DOC_SIZE = 30000;
  const size_t JSON_BUFFER_SIZE = 30000;

  DynamicJsonDocument jsonDoc(JSON_DOC_SIZE);          // Use DynamicJsonDocument for heap allocation
  char *jsonBuffer = (char *)malloc(JSON_BUFFER_SIZE); // Allocate buffer on heap

  if (!jsonBuffer)
  {
    Serial.println("Failed to allocate memory for JSON buffer!");
    free(base64Buf); // Free the base64 buffer before erroring
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }
  // --- End Dynamic JSON Allocation ---

  jsonDoc["device_id"] = MQTT_CLIENT_ID;
  jsonDoc["session_id"] = currentSessionId;
  jsonDoc["timestamp"] = millis();
  jsonDoc["session_duration"] = millis() - sessionStartTime;
  jsonDoc["image_size"] = imageLen;
  jsonDoc["image"] = base64Buf;                     // Re-enabled image sending
  jsonDoc["face_detected"] = faceDetectedInSession; // Re-enable face detection field

  // print that if we are using rfid and it is in the payload
  Serial.print("rfidDetected flag: ");
  Serial.println(rfidDetected);
  jsonDoc["rfid_detected"] = rfidDetected;
  if (rfidDetected)
  {
    jsonDoc["rfid_tag"] = FAKE_RFID_TAG_MAIN; // Use constant directly
  }

  size_t jsonLen = serializeJson(jsonDoc, jsonBuffer, JSON_BUFFER_SIZE);
  if (jsonLen == 0)
  {
    Serial.println("Failed to serialize JSON (Check ArduinoJson docs). Doc/Buffer might be too small.");
    free(jsonBuffer); // Free allocated buffer
    free(base64Buf);
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }
  else if (jsonLen >= JSON_BUFFER_SIZE)
  {
    Serial.printf("Failed to serialize JSON: Buffer too small! Need at least %d bytes.\n", jsonLen + 1);
    free(jsonBuffer); // Free allocated buffer
    free(base64Buf);
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }

  Serial.print("Free heap after JSON Doc/Buffer: "); // Check heap AFTER allocation
  Serial.println(ESP.getFreeHeap());

  delay(1); // Add delay before publishing
  Serial.printf("Publishing payload (%d bytes) to %s...\n", jsonLen, TOPIC_SESSION);
  if (mqttClient.publish(TOPIC_SESSION, jsonBuffer, jsonLen))
  {
    Serial.println("Payload published successfully.");
  }
  else
  {
    Serial.println("MQTT publish failed!");
  }

  free(jsonBuffer); // IMPORTANT: Free the dynamically allocated JSON buffer
  free(base64Buf);

  clearInputFlags();       // Use new function
  currentState = COOLDOWN; // Transition to COOLDOWN state
  lastStateChange = millis();
  Serial.println("Session complete. Entering COOLDOWN state.");
}

void handleErrorState()
{
  // --- DEBUG LOG ---
  Serial.print("[State: ERROR] RFID Pin: ");
  Serial.print(digitalRead(RFID_INPUT_PIN));
  Serial.print(" | rfidDetected Flag: ");
  Serial.println(rfidDetected);
  // --- END DEBUG LOG ---
  Serial.println("ERROR state: Attempting recovery...");
  if (millis() - lastStateChange > RETRY_DELAY)
  {
    Serial.println("Retry delay elapsed. Returning to IDLE state.");
    clearInputFlags(); // Use new function
    currentState = IDLE;
    lastStateChange = millis();
  }
}

// --- New Function: Handle Cooldown State ---
void handleCooldownState()
{
  // --- DEBUG LOG ---
  Serial.print("[State: COOLDOWN] RFID Pin: ");
  Serial.print(digitalRead(RFID_INPUT_PIN));
  Serial.print(" | rfidDetected Flag: ");
  Serial.println(rfidDetected);
  // --- END DEBUG LOG ---
  if (millis() - lastStateChange >= COOLDOWN_DURATION_MS)
  {
    Serial.println("Cooldown finished. Returning to IDLE state.");
    currentState = IDLE;
    lastStateChange = millis();
    // clear flags again
    clearInputFlags();
  }
}
// --- End New Function ---

void loop()
{
  updateLEDStatus(currentState);

  // --- GPIO Signal Handling (New Approach) ---
  bool motionSignal = (digitalRead(MOTION_INPUT_PIN) == HIGH); // Use define from config.h
  bool rfidSignal = (digitalRead(RFID_INPUT_PIN) == HIGH);     // Use define from config.h

  // print the motionSignal and rfidSignal
  Serial.print("motionSignal: ");
  Serial.println(motionSignal);
  Serial.print("rfidSignal: ");
  Serial.println(rfidSignal);

  // Optional basic debouncing / edge detection could be added here if needed

  if (motionSignal)
  {
    // Set flag - State machine (handleIdleState) will check and clear it
    motionDetected = true;
  }

  if (rfidSignal)
  {
    if (!rfidDetected)
    { // Trigger only once while signal is HIGH
      rfidDetected = true;

      Serial.println("-> RFID Signal HIGH detected.");
    }
  }
  else
  {
    // If RFID signal goes LOW, allow rfidDetected to be set again next time
    // The flag should be cleared after use in handleSessionState
    // No action needed here for clearing based on LOW signal in this logic.
  }
  // --- End GPIO Signal Handling ---

  // processSerialData(); // Removed for GPIO approach

  // Main state machine logic (Removed EMERGENCY case)
  switch (currentState)
  {
  case IDLE:
    handleIdleState();
    break;
  case CONNECTING:
    handleConnectingState();
    break;
  case IMAGE_CAPTURE:
    handleImageCaptureState();
    break;
  case SESSION:
    handleSessionState();
    break;
  case COOLDOWN: // Add case for COOLDOWN state
    handleCooldownState();
    break;
  case ERROR:
    handleErrorState();
    break;
  default:
    // Unknown state, reset to IDLE
    Serial.println("Unknown state detected! Resetting to IDLE.");
    currentState = IDLE;
    lastStateChange = millis();
    clearInputFlags(); // Clear flags on reset
    break;
  }

  delay(10);
}