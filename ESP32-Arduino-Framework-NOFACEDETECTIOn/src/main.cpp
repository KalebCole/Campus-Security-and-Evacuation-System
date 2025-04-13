#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <esp_camera.h>
#include <ArduinoJson.h>
#include <Base64.h>
#include "config.h"

// Global variables
StateMachine currentState = IDLE;
bool isEmergencyMode = false;
unsigned long lastStateChange = 0;
unsigned long lastLedToggle = 0;
bool ledState = false;
unsigned long lastRetryAttempt = 0;
unsigned long lastCaptureTime = 0;
bool faceDetected = false;
unsigned long lastFaceDetection = 0;
bool motionDetected = false;
unsigned long lastMotionCheck = 0;
unsigned long sessionStartTime = 0;
String currentSessionId = "";
bool rfidDetected = false;

// Testing configuration
const bool TESTING_MODE = false;                     // Set to false for real operation
const int TEST_MOTION_PIN = 13;                      // Using GPIO13 for testing
const unsigned long TEST_MOTION_INTERVAL = 10000;    // 10 seconds
const unsigned long TEST_RFID_INTERVAL = 15000;      // 15 seconds
const unsigned long TEST_EMERGENCY_INTERVAL = 45000; // 45 seconds

// Image capture variables
camera_fb_t *fb = NULL;
unsigned long lastImageCapture = 0;

// MQTT client objects
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Add connection status flags after global variables
bool wifiConnected = false;
bool mqttConnected = false;
unsigned long lastConnectionAttempt = 0;
const unsigned long CONNECTION_RETRY_DELAY = 5000; // 5 seconds between retry attempts

void setupLEDs()
{
  pinMode(LED_PIN, OUTPUT);
  pinMode(LED_FLASH, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(LED_FLASH, LOW);
}

void updateLEDStatus()
{
  unsigned long now = millis();

  switch (currentState)
  {
  case IDLE:
    digitalWrite(LED_PIN, LOW);
    break;

  case CONNECTION:
    if (now - lastLedToggle >= LED_SLOW_BLINK)
    {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
      lastLedToggle = now;
    }
    break;

  case FACE_DETECTING:
    if (now - lastLedToggle >= LED_NORMAL_BLINK)
    {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
      lastLedToggle = now;
    }
    break;

  case RFID_WAITING:
    if (now - lastLedToggle >= LED_FAST_BLINK)
    {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
      lastLedToggle = now;
    }
    break;

  case SESSION:
    if (now - lastLedToggle >= LED_VERY_FAST_BLINK)
    {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
      lastLedToggle = now;
    }
    break;

  case EMERGENCY:
    digitalWrite(LED_PIN, HIGH);
    break;

  case ERROR:
    if (now - lastLedToggle >= LED_ERROR_BLINK)
    {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
      lastLedToggle = now;
    }
    break;
  }
}

bool setupCamera()
{
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK)
  {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return false;
  }

  // Configure camera settings
  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL)
  {
    s->set_vflip(s, 1);
    s->set_hmirror(s, 1);
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);
    s->set_aec_value(s, 300);
    s->set_gain_ctrl(s, 1);
    s->set_agc_gain(s, 0);
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
    s->set_lenc(s, 1);
    s->set_dcw(s, 1);
    s->set_colorbar(s, 0);
  }

  return true;
}

// Connect to WiFi - Returns true on success, false otherwise
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
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    return true;
  }
  else
  {
    Serial.println("\nWiFi connection failed!");
    WiFi.disconnect(true);
    delay(100);
    return false;
  }
}

// Generate a unique session ID
String generateSessionId()
{
  String id = "SESS_";
  id += String(millis(), HEX);
  id += "_";
  id += String(random(1000, 9999));
  return id;
}

// Handle motion detection
void handleMotion()
{
  if (millis() - lastMotionCheck >= MOTION_DEBOUNCE)
  {
    int motionState = digitalRead(MOTION_PIN);
    Serial.printf("Motion state: %d\n", motionState);

    // Only check test pin if in testing mode
    if (TESTING_MODE)
    {
      int testMotionState = digitalRead(TEST_MOTION_PIN);
      combinedMotionState = motionState || testMotionState;
      Serial.printf("Motion state: %d, Test motion: %d\n", motionState, testMotionState);
    }
    // else
    // {
    //   Serial.printf("Motion state: %d\n", motionState);
    // }

    // Handle state transitions
    switch (currentState)
    {
    case IDLE:
      if (motionState == HIGH)
      {
        motionDetected = true;
        currentState = CONNECTION;
        lastStateChange = millis();
        Serial.println("Motion detected, transitioning to CONNECTION state");
      }
      break;

    case CONNECTION:
      // TODO: will need to check this to see if we need to add a timeout for motion
      if (motionState == LOW)
      {
        motionDetected = false;
        currentState = IDLE;
        lastStateChange = millis();
        Serial.println("Motion cleared, returning to IDLE");
      }
      break;

    // Other states don't need motion handling
    default:
      break;
    }

    lastMotionCheck = millis();
  }
}

// MQTT Callback function
void mqttCallback(const char *topic, byte *payload, unsigned int length)
{
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  // Convert payload to string
  char message[length + 1];
  memcpy(message, payload, length);
  message[length] = '\0';
  Serial.println(message);

  // Handle emergency messages
  if (strcmp(topic, TOPIC_EMERGENCY) == 0)
  {
    currentState = EMERGENCY;
    lastStateChange = millis();
    Serial.println("Emergency mode activated!");
  }

  // Handle RFID messages
  if (strcmp(topic, TOPIC_RFID) == 0)
  {
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, message);

    if (!error)
    {
      const char *rfid = doc["rfid"];
      if (rfid && strlen(rfid) > 0)
      {
        rfidDetected = true;
        Serial.print("Valid RFID detected: ");
        Serial.println(rfid);

        if (currentState == RFID_WAITING)
        {
          currentSessionId = generateSessionId();
          sessionStartTime = millis();
          currentState = SESSION;
          lastStateChange = millis();
          Serial.println("RFID detected, transitioning to SESSION state");
        }
      }
    }
  }
}

// Connect to MQTT Broker - Returns true on success, false otherwise
bool connectToMQTT()
{
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  Serial.println("Attempting MQTT connection...");
  if (mqttClient.connect(MQTT_CLIENT_ID))
  {
    Serial.println("MQTT connected");

    // Subscribe to required topics
    mqttClient.subscribe(TOPIC_EMERGENCY);
    mqttClient.subscribe(TOPIC_RFID);

    // Publish online status
    StaticJsonDocument<100> doc;
    doc["device_id"] = MQTT_CLIENT_ID;
    doc["status"] = "online";
    String output;
    serializeJson(doc, output);
    mqttClient.publish(TOPIC_SESSION, output.c_str());
    Serial.println("Published online status.");
    return true;
  }
  else
  {
    Serial.print("MQTT connection failed, rc=");
    Serial.print(mqttClient.state());
    Serial.println(" ");
    return false;
  }
}

// Capture and process image
bool captureAndProcessImage()
{
  // Capture image
  fb = esp_camera_fb_get();
  if (!fb)
  {
    Serial.println("Camera capture failed");
    return false;
  }

  Serial.printf("Image captured: %d bytes\n", fb->len);

  // TODO: Add face detection here
  // faceDetected = true; // Temporary for testing

  // Convert to Base64
  int encodedLength = Base64.encodedLength(fb->len);
  char *base64Buffer = (char *)malloc(encodedLength + 1);
  if (!base64Buffer)
  {
    Serial.println("Failed to allocate base64 buffer");
    esp_camera_fb_return(fb);
    return false;
  }

  Base64.encode(base64Buffer, (char *)fb->buf, fb->len);

  // Create JSON payload
  StaticJsonDocument<1024> doc;
  doc["device_id"] = MQTT_CLIENT_ID;
  doc["session_id"] = currentSessionId;
  doc["timestamp"] = millis();
  doc["image_size"] = fb->len;
  doc["image_data"] = base64Buffer;
  doc["rfid_detected"] = rfidDetected;
  doc["face_detected"] = faceDetected;

  // Publish to MQTT
  String output;
  serializeJson(doc, output);
  bool published = mqttClient.publish(TOPIC_SESSION, output.c_str());

  // Cleanup
  free(base64Buffer);
  esp_camera_fb_return(fb);

  if (!published)
  {
    Serial.println("Failed to publish image");
    return false;
  }

  Serial.println("Image published successfully");
  return true;
}

// void simulateRfidDetection()
// {
//   Serial.println("Test: Simulating RFID detection");
//   faceDetected = true; // Also need face detection

//   // Create JSON payload similar to what would come from MQTT
//   StaticJsonDocument<200> doc;
//   doc["rfid"] = "TEST_RFID_12345";

//   // Serialize to string
//   String rfidJson;
//   serializeJson(doc, rfidJson);

//   // Call the callback directly with this payload
//   const char *topic = TOPIC_RFID;
//   byte *payload = (byte *)rfidJson.c_str();
//   mqttCallback(topic, payload, rfidJson.length());
// }

// void simulateEmergency()
// {
//   Serial.println("Test: Simulating emergency button");

//   // Create emergency payload
//   StaticJsonDocument<100> doc;
//   doc["emergency"] = true;

//   // Serialize to string
//   String emergencyJson;
//   serializeJson(doc, emergencyJson);

//   // Call the callback directly
//   const char *topic = TOPIC_EMERGENCY;
//   byte *payload = (byte *)emergencyJson.c_str();
//   mqttCallback(topic, payload, emergencyJson.length());
// }

void handleSessionTimeout()
{
  if (currentState == SESSION && millis() - sessionStartTime >= SESSION_TIMEOUT)
  {
    Serial.println("Test: Session timeout, returning to IDLE");
    currentState = IDLE;
    rfidDetected = false;
    faceDetected = false;
    lastStateChange = millis();
  }
}

// Function to detect faces in the captured image
bool detectFaces(camera_fb_t *fb)
{
  if (!fb)
    return false;

  // Convert JPEG to RGB for face detection
  uint8_t *rgb_buf = NULL;
  size_t rgb_len = 0;
  bool converted = fmt2rgb888(fb->buf, fb->len, fb->format, rgb_buf);

  if (!converted || !rgb_buf)
  {
    Serial.println("Failed to convert image to RGB");
    return false;
  }

  // Simple face detection based on skin color
  int faceCount = 0;
  for (int y = 0; y < fb->height; y++)
  {
    for (int x = 0; x < fb->width; x++)
    {
      int idx = (y * fb->width + x) * 3;
      uint8_t r = rgb_buf[idx];
      uint8_t g = rgb_buf[idx + 1];
      uint8_t b = rgb_buf[idx + 2];

      // Basic skin color detection
      if (r > 95 && g > 40 && b > 20 &&
          r > g && r > b &&
          abs(r - g) > 15)
      {
        faceCount++;
      }
    }
  }

  free(rgb_buf);

  // If we found enough skin-colored pixels, consider it a face
  return (faceCount > (fb->width * fb->height * 0.01)); // 1% of image area
}

// Session management functions
void cleanupSession()
{
  currentSessionId = "";
  rfidDetected = false;
  faceDetected = false;
  sessionStartTime = 0;
  Serial.println("Session cleaned up");
}

bool canStartSession()
{
  // Check if we have enough memory for a new session
  if (ESP.getFreeHeap() < 20000)
  { // 20KB minimum free heap
    Serial.println("Not enough memory for new session");
    return false;
  }

  // Check if we have valid connections
  if (!wifiConnected || !mqttConnected)
  {
    Serial.println("No valid connections for session");
    return false;
  }

  return true;
}

void handleSessionState()
{
  // Check for session timeout
  if (millis() - sessionStartTime >= SESSION_TIMEOUT)
  {
    cleanupSession();
    currentState = IDLE;
    lastStateChange = millis();
    Serial.println("Session timeout, returning to IDLE");
    return;
  }

  // Check if we can continue the session
  if (!canStartSession())
  {
    cleanupSession();
    currentState = ERROR;
    lastStateChange = millis();
    Serial.println("Session error, transitioning to ERROR state");
    return;
  }

  // Capture and publish images periodically
  static unsigned long lastCaptureTime = 0;
  if (millis() - lastCaptureTime >= IMAGE_CAPTURE_INTERVAL)
  {
    captureAndProcessImage();
    lastCaptureTime = millis();
  }
}

void captureAndPublishImage()
{
  if (!canStartSession())
  {
    Serial.println("Cannot capture image - session requirements not met");
    return;
  }

  // Capture image
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb)
  {
    Serial.println("Failed to capture image");
    return;
  }

  // Detect faces
  bool hasFaces = detectFaces(fb);

  // Encode image to Base64
  size_t encodedSize = Base64.encodedLength(fb->len);
  char *encodedImage = (char *)malloc(encodedSize);
  if (!encodedImage)
  {
    Serial.println("Failed to allocate memory for base64 encoding");
    esp_camera_fb_return(fb);
    return;
  }

  Base64.encode(encodedImage, (char *)fb->buf, fb->len);

  // Create JSON payload with enhanced session information
  StaticJsonDocument<1024> doc;
  doc["device_id"] = MQTT_CLIENT_ID;
  doc["session_id"] = currentSessionId;
  doc["timestamp"] = millis();
  doc["session_duration"] = millis() - sessionStartTime;
  doc["image_size"] = fb->len;
  doc["image_data"] = encodedImage;
  doc["rfid_detected"] = rfidDetected;
  doc["face_detected"] = hasFaces;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["state"] = "SESSION";

  String output;
  serializeJson(doc, output);

  // Publish to MQTT
  if (!mqttClient.publish(TOPIC_SESSION, output.c_str()))
  {
    Serial.println("Failed to publish image");
  }

  // Clean up
  free(encodedImage);
  esp_camera_fb_return(fb);
}

// State handler functions
void handleIdleState()
{
  // In IDLE state, just check motion sensor
  if (motionDetected)
  {
    currentState = CONNECTION;
    lastStateChange = millis();
    Serial.println("Motion detected, transitioning to CONNECTION state");
  }
}

void handleConnectionState()
{
  // Try to establish connections
  if (!wifiConnected)
  {
    wifiConnected = connectToWiFi();
    if (!wifiConnected)
    {
      currentState = ERROR;
      lastStateChange = millis();
      return;
    }
  }

  if (!mqttConnected)
  {
    mqttConnected = connectToMQTT();
    if (!mqttConnected)
    {
      currentState = ERROR;
      lastStateChange = millis();
      return;
    }
  }

  // If both connections are established, move to FACE_DETECTING
  if (wifiConnected && mqttConnected)
  {
    currentState = FACE_DETECTING;
    lastStateChange = millis();
    Serial.println("Connections established, transitioning to FACE_DETECTING state");
  }
}

void handleFaceDetectingState()
{
  // Check for face detection timeout
  if (millis() - lastStateChange >= FACE_DETECTION_TIMEOUT)
  {
    currentState = RFID_WAITING;
    lastStateChange = millis();
    Serial.println("Face detection timeout, returning to RFID_WAITING");
    return;
  }

  // Try to detect faces
  camera_fb_t *fb = esp_camera_fb_get();
  if (fb)
  {
    bool hasFaces = detectFaces(fb);
    esp_camera_fb_return(fb);

    if (hasFaces)
    {
      faceDetected = true;
      currentState = RFID_WAITING;
      lastStateChange = millis();
      Serial.println("Face detected, transitioning to RFID_WAITING state");
    }
  }
  // TODO: do i need to wrorry about error or emergency here?
}

void handleRfidWaitingState()
{
  // Check for RFID timeout
  if (millis() - lastStateChange >= RFID_TIMEOUT)
  {
    currentState = SESSION;
    lastStateChange = millis();
    Serial.println("RFID timeout, returning to SESSION");
    return;
  }

  // RFID detection is handled in MQTT callback
  if (rfidDetected)
  {
    currentSessionId = generateSessionId();
    sessionStartTime = millis();
    currentState = SESSION;
    lastStateChange = millis();
    Serial.println("RFID detected, transitioning to SESSION state");
  }
}

void handleEmergencyState()
{
  // Check for emergency timeout
  if (millis() - lastStateChange >= EMERGENCY_TIMEOUT)
  {
    currentState = IDLE;
    lastStateChange = millis();
    Serial.println("Emergency timeout, returning to IDLE");
  }
}

void handleErrorState()
{
  // Try to recover from error
  if (WiFi.status() == WL_CONNECTED && mqttClient.connected())
  {
    currentState = IDLE;
    lastStateChange = millis();
    Serial.println("Error recovered, returning to IDLE");
  }
}

void handleStateTransition()
{
  switch (currentState)
  {
  case IDLE:
    if (motionDetected)
    {
      currentState = CONNECTION;
      Serial.println("Transition: IDLE -> CONNECTION");
    }
    break;

  case CONNECTION:
    if (WiFi.status() == WL_CONNECTED && mqttClient.connected())
    {
      currentState = FACE_DETECTING;
      Serial.println("Transition: CONNECTION -> FACE_DETECTING");
      faceDetected = false; // Reset face detection status
    }
    break;

  case FACE_DETECTING:
    if (faceDetected || millis() - lastStateChange >= FACE_DETECTION_TIMEOUT)
    {
      currentState = RFID_WAITING;
      Serial.println("Transition: FACE_DETECTING -> RFID_WAITING");
      rfidDetected = false; // Reset RFID detection status
    }
    break;

  case RFID_WAITING:
    if (rfidDetected || millis() - lastStateChange >= RFID_TIMEOUT)
    {
      currentState = SESSION;
      Serial.println("Transition: RFID_WAITING -> SESSION");
    }
    break;

  case SESSION:
    if (millis() - lastStateChange >= SESSION_TIMEOUT)
    {
      currentState = IDLE;
      Serial.println("Transition: SESSION -> IDLE");
    }
    break;

  case EMERGENCY:
    if (millis() - lastStateChange >= EMERGENCY_TIMEOUT)
    {
      currentState = IDLE;
      Serial.println("Transition: EMERGENCY -> IDLE");
    }
    break;

  case ERROR:
    if (WiFi.status() == WL_CONNECTED && mqttClient.connected())
    {
      currentState = IDLE;
      Serial.println("Transition: ERROR -> IDLE");
    }
    break;
  }
}

void handleFaceDetection()
{
  if (currentState == FACE_DETECTING)
  {
    // Perform face detection
    bool detected = detectFaces(fb); // Use the existing detectFaces function
    if (detected)
    {
      faceDetected = true;
      Serial.println("Face detected");
    }
  }
}

void handleRfidMessage(const char *topic, byte *payload, unsigned int length)
{
  if (currentState == RFID_WAITING && strcmp(topic, TOPIC_RFID) == 0)
  {
    rfidDetected = true;
    Serial.println("RFID detected");
  }
}

void setup()
{
  Serial.begin(115200);
  delay(1000);

  // Try to connect to WiFi first
  wifiConnected = connectToWiFi();
  if (!wifiConnected)
  {
    Serial.println("WiFi connection failed in setup");
  }
  else
  {
    Serial.println("WiFi connected in setup");
    mqttConnected = connectToMQTT();
  }

  // Setup motion sensor
  pinMode(MOTION_PIN, INPUT);
  // if (TESTING_MODE)
  // {
  //   pinMode(TEST_MOTION_PIN, OUTPUT);
  //   Serial.println("Testing mode enabled - using simulated inputs");
  // }
  Serial.println("Motion sensor initialized");

  setupLEDs();
  Serial.println("LEDs initialized");

  if (!setupCamera())
  {
    currentState = ERROR;
    lastStateChange = millis();
    Serial.println("Entering ERROR state due to camera init failure.");
    return;
  }
  Serial.println("Camera initialized successfully");

  currentState = IDLE;
  lastStateChange = millis();
  Serial.println("State: IDLE");
}

void loop()
{
  // Process current state
  switch (currentState)
  {
  case IDLE:
    handleIdleState();
    break;
  case CONNECTION:
    handleConnectionState();
    break;
  case FACE_DETECTING:
    handleFaceDetectingState();
    break;
  case RFID_WAITING:
    handleRfidWaitingState();
    break;
  case SESSION:
    handleSessionState();
    break;
  case EMERGENCY:
    handleEmergencyState();
    break;
  case ERROR:
    handleErrorState();
    break;
  }

  // Update LED status
  updateLEDStatus();

  // Process MQTT messages
  if (mqttClient.connected())
  {
    mqttClient.loop();
  }
}