#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <esp_camera.h>
#include <ArduinoJson.h>
#include <base64.hpp>

// Test topic - separate from your main topics
const char* MQTT_TEST_TOPIC = "campus/security/test";

// WiFi credentials
const char* WIFI_SSID = "iPod Mini";
const char* WIFI_PASSWORD = "H0t$p0t!";

// MQTT settings
const char* MQTT_BROKER = "172.20.10.2";
const int MQTT_PORT = 1883;
const char* MQTT_TOPIC = "campus/security/face";
const char* MQTT_STATUS_TOPIC = "campus/security/status";
const char* MQTT_AUTH_TOPIC = "campus/security/auth";
const char* DEVICE_ID = "esp32cam_1";
const char* DEVICE_SECRET = "YOUR_DEVICE_SECRET";

// MQTT client objects
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// LED pin definition
#define LED_PIN 2  // Built-in LED (white LED next to the camera)
#define LED_FLASH 4  // Flash LED (larger LED on the back)

// Camera Pin Definitions based on working MicroPython example
#define PWDN_GPIO_NUM     -1 // From MicroPython example
#define RESET_GPIO_NUM    -1 // NC
#define XCLK_GPIO_NUM     21 // From MicroPython example
#define SIOD_GPIO_NUM     26 // SDA - Matches MicroPython
#define SIOC_GPIO_NUM     27 // SCL - Matches MicroPython

// Data pins from MicroPython d0-d7 sequence
#define Y2_GPIO_NUM        4 // D0 from MicroPython
#define Y3_GPIO_NUM        5 // D1 from MicroPython
#define Y4_GPIO_NUM       18 // D2 from MicroPython
#define Y5_GPIO_NUM       19 // D3 from MicroPython
#define Y6_GPIO_NUM       36 // D4 from MicroPython
#define Y7_GPIO_NUM       39 // D5 from MicroPython
#define Y8_GPIO_NUM       34 // D6 from MicroPython
#define Y9_GPIO_NUM       35 // D7 from MicroPython

// Control pins - Match MicroPython
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// State Machine Definition
enum DeviceState {
  INIT,
  WIFI_CONNECTING,
  MQTT_CONNECTING,
  READY,
  ERROR
};
DeviceState currentState = INIT;
unsigned long lastStateChange = 0; // Track time in current state
unsigned long lastRetryAttempt = 0; // Track time for retries
const unsigned long RETRY_DELAY = 5000; // 5 seconds between retries
unsigned long lastCaptureTime = 0; // Track time for image capture
const unsigned long CAPTURE_INTERVAL = 5000; // Capture image every 5 seconds

void setupLEDs() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(LED_FLASH, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(LED_FLASH, LOW);
}

void blinkLED(int pin, int duration) {
  digitalWrite(pin, HIGH);
  delay(duration);
  digitalWrite(pin, LOW);
  delay(duration);
}

// Update LED based on state
void updateLEDStatus() {
  switch (currentState) {
    case WIFI_CONNECTING:
      // Fast blink
      digitalWrite(LED_PIN, (millis() / 250) % 2);
      break;
    case MQTT_CONNECTING:
      // Medium blink
      digitalWrite(LED_PIN, (millis() / 500) % 2);
      break;
    case READY:
      // Solid ON
      digitalWrite(LED_PIN, HIGH);
      break;
    case ERROR:
      // Very fast blink
       digitalWrite(LED_PIN, (millis() / 100) % 2);
      break;
    default: // INIT or others
      // Solid OFF
      digitalWrite(LED_PIN, LOW);
      break;
  }
}

// Setup Camera Function - Returns true on success
// TODO: remove all the micropython comments and make comments that are relevant to the code
bool setupCamera() {
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
    config.xclk_freq_hz = 20000000; // Matches MicroPython XCLK_20MHz
    config.pixel_format = PIXFORMAT_JPEG; // Match MicroPython format
    config.frame_size = FRAMESIZE_VGA;    // Match MicroPython framesize
    config.jpeg_quality = 10; // Match MicroPython quality
    config.fb_count = 1;      // Use 1 frame buffer for simplicity (MicroPython might use PSRAM differently)
    // config.fb_location = CAMERA_FB_IN_PSRAM; // Uncomment if PSRAM issues persist and board has PSRAM

    // Initialize Camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        return false;
    }
    Serial.println("Camera initialized successfully.");

    // Apply sensor settings like flip/mirror from MicroPython example
    sensor_t * s = esp_camera_sensor_get();
    if (s != NULL) {
      s->set_vflip(s, 1);   // Match camera.flip(1)
      s->set_hmirror(s, 1); // Match camera.mirror(1)
      // Other settings like saturation, brightness, contrast can be set here if needed
      // s->set_saturation(s, 0); // Example
      Serial.println("Applied flip and mirror settings.");
    } else {
      Serial.println("Warning: Could not get sensor handle to set flip/mirror.");
    }

    return true;
}

// Capture and Publish Image Function
void captureAndPublishImage() {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Camera capture failed");
        // Consider transitioning to ERROR state if this happens repeatedly
        return;
    }
    Serial.printf("Captured frame: %dx%d, len: %d bytes\n", fb->width, fb->height, fb->len);

    
    // Calculate the required buffer size for base64 encoding
    // Each 3 bytes of data becomes 4 bytes in base64
    size_t base64Len = encode_base64_length(fb->len);
    char *base64Buf = (char *)malloc(base64Len + 1); // +1 for null terminator
    
    if (!base64Buf) {
        Serial.println("Failed to allocate memory for Base64 buffer");
        esp_camera_fb_return(fb);
        return;
    }    
    
    // Encode the frame buffer to base64
    encode_base64(fb->buf, fb->len, (unsigned char*)base64Buf);
    base64Buf[base64Len] = '\0'; // Ensure null termination
    Serial.printf("Base64 Encoded Length: %d\n", base64Len);
    // Construct JSON payload
    String payload = "{";
    payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
    payload += "\"timestamp\": " + String(millis()) + ",";
    payload += "\"format\": \"jpeg\",";
    payload += "\"image\":\"" + String(base64Buf) + "\"";
    payload += "}";

    
    // Free the base64 buffer
    free(base64Buf);
    // Publish the payload
    Serial.println("Publishing image payload...");
    bool published = mqttClient.publish(MQTT_TOPIC, payload.c_str());

    if (published) {
        Serial.println("Image payload published successfully.");
    } else {
        Serial.println("Image payload publication failed! (Likely too large for MQTT buffer/settings)");
        // You might want to check mqttClient.state() here too
    }

    // Return the frame buffer back to the camera library
    esp_camera_fb_return(fb);
}

// Basic MQTT Callback function
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();

  // TODO: Handle specific topic messages later
}

// Connect to MQTT Broker - Returns true on success, false otherwise
bool connectToMQTT() { // Changed return type
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback); // Assign the callback

  Serial.println("Attempting MQTT connection...");
  if (mqttClient.connect(DEVICE_ID)) {
    Serial.println("MQTT connected");
    // *** Publish status on successful connection ***
    StaticJsonDocument<100> doc;
    doc["device_id"] = DEVICE_ID;
    doc["status"] = "online";
    String output;
    serializeJson(doc, output);
    mqttClient.publish(MQTT_STATUS_TOPIC, output.c_str());
    Serial.println("Published online status.");
    // Example: Subscribe to a topic if needed later
    // mqttClient.subscribe(MQTT_STATUS_TOPIC);
    return true; // Indicate success
  } else {
    Serial.print("MQTT connection failed, rc=");
    Serial.print(mqttClient.state());
    Serial.println(" "); // Removed retry message here, handled by state machine
    return false; // Indicate failure
  }
}

// Connect to WiFi - Returns true on success, false otherwise
bool connectToWiFi() { // Changed return type
  Serial.println("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  // Use a timeout instead of fixed attempts for potentially long connection times
  unsigned long wifiStartTime = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - wifiStartTime < 30000)) { // 30 second timeout
    // updateLEDStatus handles blinking now
    Serial.print(".");
    delay(500); // Short delay between checks
    attempts++; // Still useful for logging maybe
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    return true; // Indicate success
  } else {
    Serial.println("\nWiFi connection failed!");
    WiFi.disconnect(true); // Ensure clean disconnect on failure
    delay(100);
    return false; // Indicate failure
  }
}

// Function to test different MQTT payload sizes
void testMqttPayloadSizes() {
  Serial.println("\n--- Starting MQTT Payload Size Tests ---");
  
  // Test 1: Tiny payload (under 100 bytes)
  String tinyPayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"test\":\"hello\"}";
  int tinySize = tinyPayload.length();
  Serial.printf("Test 1: Tiny payload - %d bytes\n", tinySize);
  bool tinySuccess = mqttClient.publish(MQTT_TEST_TOPIC, tinyPayload.c_str());
  Serial.printf("Result: %s\n\n", tinySuccess ? "SUCCESS" : "FAILED");
  delay(1000);
  
  // Test 2: Small payload (about 500 bytes)
  String smallPayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"data\":\"";
  for (int i = 0; i < 450; i++) {
    smallPayload += "A";
  }
  smallPayload += "\"}";
  int smallSize = smallPayload.length();
  Serial.printf("Test 2: Small payload - %d bytes\n", smallSize);
  bool smallSuccess = mqttClient.publish(MQTT_TEST_TOPIC, smallPayload.c_str());
  Serial.printf("Result: %s\n\n", smallSuccess ? "SUCCESS" : "FAILED");
  delay(1000);
  
  // Test 3: Medium payload (about 1KB)
  String mediumPayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"data\":\"";
  for (int i = 0; i < 950; i++) {
    mediumPayload += "B";
  }
  mediumPayload += "\"}";
  int mediumSize = mediumPayload.length();
  Serial.printf("Test 3: Medium payload - %d bytes\n", mediumSize);
  bool mediumSuccess = mqttClient.publish(MQTT_TEST_TOPIC, mediumPayload.c_str());
  Serial.printf("Result: %s\n\n", mediumSuccess ? "SUCCESS" : "FAILED");
  delay(1000);
  
  // Test 4: Large payload (about 5KB)
  String largePayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"data\":\"";
  for (int i = 0; i < 4900; i++) {
    largePayload += "C";
  }
  largePayload += "\"}";
  int largeSize = largePayload.length();
  Serial.printf("Test 4: Large payload - %d bytes\n", largeSize);
  bool largeSuccess = mqttClient.publish(MQTT_TEST_TOPIC, largePayload.c_str());
  Serial.printf("Result: %s\n\n", largeSuccess ? "SUCCESS" : "FAILED");
  delay(1000);
  
  // Test 5: Very large payload (about 10KB)
  String veryLargePayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"data\":\"";
  for (int i = 0; i < 9900; i++) {
    veryLargePayload += "D";
  }
  veryLargePayload += "\"}";
  int veryLargeSize = veryLargePayload.length();
  Serial.printf("Test 5: Very large payload - %d bytes\n", veryLargeSize);
  bool veryLargeSuccess = mqttClient.publish(MQTT_TEST_TOPIC, veryLargePayload.c_str());
  Serial.printf("Result: %s\n\n", veryLargeSuccess ? "SUCCESS" : "FAILED");
  
  Serial.println("--- MQTT Payload Size Tests Complete ---");
  Serial.printf("Tiny (%d bytes): %s\n", tinySize, tinySuccess ? "SUCCESS" : "FAILED");
  Serial.printf("Small (%d bytes): %s\n", smallSize, smallSuccess ? "SUCCESS" : "FAILED");
  Serial.printf("Medium (%d bytes): %s\n", mediumSize, mediumSuccess ? "SUCCESS" : "FAILED");
  Serial.printf("Large (%d bytes): %s\n", largeSize, largeSuccess ? "SUCCESS" : "FAILED");
  Serial.printf("Very Large (%d bytes): %s\n", veryLargeSize, veryLargeSuccess ? "SUCCESS" : "FAILED");
}

void setup() {
  // Initialize Serial
  Serial.begin(115200);
  delay(1000);  // Give time for Serial to initialize
  Serial.println("\nESP32-CAM State Machine Client");
  
  // Set MQTT buffer size
  if (!mqttClient.setBufferSize(30000)) {
    Serial.println("Failed to set MQTT buffer size!");
  } else {
    Serial.println("MQTT buffer size set to 30000 bytes");
  }
  // Setup LEDs
  setupLEDs();
  
  // Setup Camera FIRST
  if (!setupCamera()) {
    currentState = ERROR;
    lastStateChange = millis();
    Serial.println("Entering ERROR state due to camera init failure.");
    // Loop will handle the ERROR state indication/behavior
    return; // Skip further setup if camera failed
  }
  
  // Start state machine (only if camera setup succeeded)
  currentState = WIFI_CONNECTING; 
  lastStateChange = millis();
  Serial.println("State: WIFI_CONNECTING");
  // Initial connection attempts are handled in loop
}

void loop() {
  unsigned long now = millis();

  // Update LED based on current state regardless of other logic
  updateLEDStatus();

  // Main State Machine Logic
  switch (currentState) {
    case WIFI_CONNECTING:
      if (connectToWiFi()) {
        currentState = MQTT_CONNECTING;
        lastStateChange = now;
        lastRetryAttempt = now; // Reset retry timer for MQTT
        Serial.println("State: MQTT_CONNECTING");
      } else {
        // Optional: Add retry limit or go straight to ERROR
        Serial.println("WiFi failed, retrying after delay...");
        delay(RETRY_DELAY); // Wait before next attempt in this state
      }
      break;

    case MQTT_CONNECTING:
       // Only attempt connection periodically
      if (now - lastRetryAttempt > RETRY_DELAY) {
        lastRetryAttempt = now;
        if (connectToMQTT()) {
          currentState = READY;
          lastStateChange = now;
          Serial.println("State: READY");
        } else {
          // Optional: Add retry limit or transition to ERROR
          Serial.println("MQTT failed, will retry..."); 
          // Stay in MQTT_CONNECTING state
        }
      } else if (!mqttClient.connected() && !espClient.connected()) {
           // If underlying TCP is also down, maybe try reconnecting sooner or go to ERROR
           Serial.println("TCP connection seems down, forcing retry attempt.");
           lastRetryAttempt = now - RETRY_DELAY; // Force retry on next loop iteration
      }
      break;

    case READY:
      // Check if MQTT connection is still alive
      if (!mqttClient.connected()) {
        Serial.println("MQTT Disconnected!");
        currentState = MQTT_CONNECTING; // Try to reconnect
        lastStateChange = now;
        lastRetryAttempt = now;
         Serial.println("State: MQTT_CONNECTING");
      } else {
        // Keep MQTT connection alive
        mqttClient.loop();
        
        // Run the payload test if in test mode
        static bool testRun = false;  // Set to true to run test once
        if (testRun) {
          testMqttPayloadSizes();
          testRun = false;  // Set to false after running test once
        }
        // Run normal camera capture
        else if (now - lastCaptureTime > CAPTURE_INTERVAL) {
            lastCaptureTime = now;
            Serial.println("--- Initiating Capture & Publish ---");
            captureAndPublishImage();
            Serial.println("--- Capture & Publish Cycle Complete ---");
        }
      }
      break;

    case ERROR:
      Serial.println("State: ERROR - System halted. Restart required or implement recovery logic.");
      // Example: Blink rapidly, wait a long time, then try restarting
      delay(10000); // Stay in error state for a while
      // Consider adding logic to attempt recovery (e.g., go back to WIFI_CONNECTING)
      // currentState = WIFI_CONNECTING; // Example recovery attempt
      // lastStateChange = now;
      break;

    case INIT:
      // Should not normally be in this state in loop
      currentState = WIFI_CONNECTING;
      lastStateChange = now;
      Serial.println("State: WIFI_CONNECTING (from INIT)");
      break;
  }
  
  // Small delay to prevent busy-waiting, but allow responsiveness
  delay(50); 
}

// We'll implement these core functions first:
// void setupCamera();
// void connectToWifi(); // Refactored above
// void connectToMQTT(); // Refactored above
// void captureAndCheckForFaces();
// void publishToMQTT(const char* topic, const char* message);