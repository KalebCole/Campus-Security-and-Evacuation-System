#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Base64.h>
#include <Esp.h> // Include for ESP.getFreeHeap()
#include "config.h"
#include <eloquent_esp32cam.h>
#include <eloquent_esp32cam/camera/pinout.h>
// #include "esp_camera.h" // No longer needed
#include "wifi/wifi.h"
#include "mqtt/mqtt.h"
#include "leds/led_control.h"
// #include "serial_handler/serial_handler.h" // Removed for GPIO approach

using eloq::camera;
// using eloq::face::detection; // Removed face detection

// State machine related variables
StateMachine currentState = IDLE;
unsigned long lastStateChange = 0;
// bool faceDetectedInSession = false; // Removed face detection

// GPIO Input Pins (New approach - Using defines from config.h)
// const int MOTION_INPUT_PIN_MAIN = 18; // Now defined in config.h
// const int RFID_INPUT_PIN_MAIN = 19; // Now defined in config.h

// --- Flags & Data (Defined here, declared extern in config.h) ---
bool motionDetected = false;
bool rfidDetected = false;
// char rfidTag[MAX_RFID_TAG_LENGTH + 1] = {0}; // Removed - Using constant FAKE_RFID_TAG_MAIN directly

// --- Fake Data (For GPIO testing without Mega connected) ---
const char *FAKE_RFID_TAG_MAIN = "FAKE123"; // Hardcoded tag for GPIO approach

// Session management variables
String currentSessionId = "";
unsigned long sessionStartTime = 0;

// Add these constants before the function definition
const int CAPTURE_RETRY_COUNT = 3;
const int CAPTURE_RETRY_DELAY_MS = 100;
/**
 * Clear GPIO input event flags and RFID tag buffer
 */
void clearInputFlags()
{
  motionDetected = false;
  rfidDetected = false;
  // memset(rfidTag, 0, sizeof(rfidTag)); // Removed - No buffer to clear
  // Optional: Print statement if needed for debugging
  // Serial.println(F("--- Cleared Input Flags ---"));
}

void setupCamera()
{
  camera.pinout.aithinker();
  camera.resolution.qvga(); // Corrected to QVGA
  // detection.fast(); // Removed face detection
  // detection.confidence(0.7); // Removed face detection

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
  setupLEDs(); // Re-enable LEDs
  // setupCamera(); // Keep commented out - called later in handleFaceDetectingState
  // setupSerialHandler(); // Removed for GPIO approach

  // Configure GPIO Inputs using defines from config.h
  pinMode(MOTION_INPUT_PIN, INPUT_PULLDOWN);
  pinMode(RFID_INPUT_PIN, INPUT_PULLDOWN);

  // Initialize random seed
  randomSeed(analogRead(0));

  // Set initial state to IDLE
  currentState = IDLE;
  lastStateChange = millis();
  clearInputFlags(); // Use new function
  // print the free heap
  Serial.print("Free heap: ");
  Serial.println(ESP.getFreeHeap());
  Serial.println("==========");
  // print if it has psram
  Serial.print("PSRAM: ");
  Serial.println(psramFound() ? "Yes" : "No");
  Serial.println("==========");

  // Initialize Camera ONCE here
  setupCamera();

  Serial.println("ESP32-CAM System initialized. Waiting for motion detection...");
}

void handleIdleState()
{
  Serial.println("Idle state: Waiting for motion detection...");
  // print motionDetected flag
  Serial.print("motionDetected flag: ");
  Serial.println(motionDetected);
  // Wait for motion detection flag from GPIO read
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
  currentState = IMAGE_CAPTURE;
  lastStateChange = millis();
}

void handleImageCaptureState()
{
  Serial.println("Capturing image..."); // Modified log message
  // setup camera - REMOVED, now done in main setup()
  // Capture image
  bool captureSuccess = false;
  // Add delay before capture
  delay(1000);
  for (int i = 0; i < CAPTURE_RETRY_COUNT; i++)
  {
    Serial.printf("Attempting image capture (%d/%d)...\n", i + 1, CAPTURE_RETRY_COUNT);

    // capture the frame
    // note: when calling capture(), the frame buffer is auto freed and then allocated again (based on the wrapper implementation)
    if (!camera.capture().isOk())
    {
      Serial.print("Capture failed: ");
      Serial.println(camera.exception.toString());
      delay(CAPTURE_RETRY_DELAY_MS);
      continue;
    }

    // check if frame is valid
    if (!camera.frame)
    {
      Serial.println("Error: No camera frame buffer available!");
      // no need to return, just try again
      delay(CAPTURE_RETRY_DELAY_MS);
      continue;
    }

    // check if the frame is more than 0 bytes
    if (camera.frame->len == 0)
    {
      Serial.println("Error: Frame buffer is empty!");
      // no need to return, just try again
      delay(CAPTURE_RETRY_DELAY_MS);
      continue;
    }

    // so image capture is succesful now

    Serial.println("Image captured successfully.");
    captureSuccess = true;
    break;
  }

  if (!captureSuccess)
  {
    Serial.println("Failed to capture image after retries.");
    currentState = ERROR;
    lastStateChange = millis();
    return;
  }

  // so image capture is successful now

  /* // Removed face detection block
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
    */

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
  delay(1); // Add delay after encoding
  Serial.printf("Image Size (bytes): %d\n", imageLen);
  Serial.printf("Base64 Size (bytes): %d\n", base64Len);
  delay(1);                                // Add delay after encoding
  Serial.print("Free heap before JSON: "); // Check heap BEFORE JSON doc/buffer
  Serial.println(ESP.getFreeHeap());

  // --- Dynamic JSON Allocation ---
  const size_t JSON_DOC_SIZE = 30000;    // Increased size
  const size_t JSON_BUFFER_SIZE = 30000; // Increased size

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
  jsonDoc["image"] = base64Buf; // Re-enabled image sending
  // jsonDoc["face_detected"] = faceDetectedInSession; // Removed face detection

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

  clearInputFlags(); // Use new function
  currentState = IDLE;
  lastStateChange = millis();
  Serial.println("Session complete. Returning to IDLE state.");
}

void handleErrorState()
{
  Serial.println("ERROR state: Attempting recovery...");
  if (millis() - lastStateChange > RETRY_DELAY)
  {
    Serial.println("Retry delay elapsed. Returning to IDLE state.");
    clearInputFlags(); // Use new function
    currentState = IDLE;
    lastStateChange = millis();
  }
}

void loop()
{
  updateLEDStatus(currentState);

  // --- GPIO Signal Handling (New Approach) ---
  bool motionSignal = (digitalRead(MOTION_INPUT_PIN) == HIGH); // Use define from config.h
  bool rfidSignal = (digitalRead(RFID_INPUT_PIN) == HIGH);     // Use define from config.h

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
      // strcpy(rfidTag, FAKE_RFID_TAG_MAIN); // Removed - Not using buffer
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