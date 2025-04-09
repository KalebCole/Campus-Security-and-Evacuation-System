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
const unsigned long CAPTURE_INTERVAL = 1000; // Capture image every 1 second

// Face detection variables
bool faceDetected = false;
unsigned long lastFaceDetection = 0;
const unsigned long FACE_DETECTION_COOLDOWN = 5000; // 5 seconds cooldown between face detections

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
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_VGA; // 320x240 for face detection
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_PSRAM;

    // Initialize Camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        return false;
    }
    Serial.println("Camera initialized successfully.");

    // Configure camera settings for face detection
    sensor_t *s = esp_camera_sensor_get();
    if (s != NULL) {
        s->set_vflip(s, 1);
        s->set_hmirror(s, 1);
        s->set_brightness(s, 0);     // -2 to 2
        s->set_contrast(s, 0);       // -2 to 2
        s->set_saturation(s, 0);     // -2 to 2
        s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect, 1 - Negative, 2 - Grayscale, 3 - Red Tint, 4 - Green Tint, 5 - Blue Tint, 6 - Sepia)
        s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
        s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
        s->set_wb_mode(s, 0);        // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
        s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
        s->set_aec2(s, 0);           // 0 = disable , 1 = enable
        s->set_ae_level(s, 0);       // -2 to 2
        s->set_aec_value(s, 300);    // 0 to 1200
        s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
        s->set_agc_gain(s, 0);       // 0 to 30
        s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
        s->set_bpc(s, 0);            // 0 = disable , 1 = enable
        s->set_wpc(s, 1);            // 0 = disable , 1 = enable
        s->set_raw_gma(s, 1);        // 0 = disable , 1 = enable
        s->set_lenc(s, 1);           // 0 = disable , 1 = enable
        s->set_dcw(s, 1);            // 0 = disable , 1 = enable
        s->set_colorbar(s, 0);       // 0 = disable , 1 = enable
    }

    return true;
}

// Function to detect faces in the captured image
bool detectFaces(camera_fb_t *fb) {
    if (!fb) return false;

    // Convert JPEG to RGB for face detection
    uint8_t *rgb_buf = NULL;
    size_t rgb_len = 0;
    bool converted = fmt2rgb888(fb->buf, fb->len, fb->format, &rgb_buf, &rgb_len);
    
    if (!converted || !rgb_buf) {
        Serial.println("Failed to convert image to RGB");
        return false;
    }
    // TODO: IMPROVE THIS FACE DETECTION ALGORITHM - DO I JUST USE ESP32 WHO?>???
    // Simple face detection based on skin color
    // This is a basic implementation - you might want to improve it
    int faceCount = 0;
    for (int y = 0; y < fb->height; y++) {
        for (int x = 0; x < fb->width; x++) {
            int idx = (y * fb->width + x) * 3;
            uint8_t r = rgb_buf[idx];
            uint8_t g = rgb_buf[idx + 1];
            uint8_t b = rgb_buf[idx + 2];
            
            // Basic skin color detection
            if (r > 95 && g > 40 && b > 20 && 
                r > g && r > b && 
                abs(r - g) > 15) {
                faceCount++;
            }
        }
    }

    free(rgb_buf);
    
    // If we found enough skin-colored pixels, consider it a face
    return (faceCount > (fb->width * fb->height * 0.01)); // 1% of image area
}

// Capture and Publish Image Function
void captureAndPublishImage() {
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("Camera capture failed");
        return;
    }

    // Check for faces
    faceDetected = detectFaces(fb);
    
    if (faceDetected) {
        Serial.println("Face detected!");
        digitalWrite(LED_FLASH, HIGH); // Flash LED when face detected
        
        // Calculate the required buffer size for base64 encoding
        size_t base64Len = encode_base64_length(fb->len);
        char *base64Buf = (char *)malloc(base64Len + 1);
        
        if (!base64Buf) {
            Serial.println("Failed to allocate memory for Base64 buffer");
            esp_camera_fb_return(fb);
            return;
        }
        
        // Encode the frame buffer to base64
        encode_base64(fb->buf, fb->len, (unsigned char*)base64Buf);
        base64Buf[base64Len] = '\0';
        
        // Construct JSON payload with face detection info
        String payload = "{";
        payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
        payload += "\"timestamp\": " + String(millis()) + ",";
        payload += "\"format\": \"jpeg\",";
        payload += "\"face_detected\": true,";
        payload += "\"image\":\"" + String(base64Buf) + "\"";
        payload += "}";

        // Free the base64 buffer
        free(base64Buf);
        
        // Publish the payload
        bool published = mqttClient.publish(MQTT_TOPIC, payload.c_str());
        if (published) {
            Serial.println("Image with face published successfully.");
        } else {
            Serial.println("Image publication failed!");
        }
        
        digitalWrite(LED_FLASH, LOW);
    } else {
        Serial.println("No face detected.");
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
}

// Connect to MQTT Broker - Returns true on success, false otherwise
bool connectToMQTT() {
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);

    Serial.println("Attempting MQTT connection...");
    if (mqttClient.connect(DEVICE_ID)) {
        Serial.println("MQTT connected");
        StaticJsonDocument<100> doc;
        doc["device_id"] = DEVICE_ID;
        doc["status"] = "online";
        String output;
        serializeJson(doc, output);
        mqttClient.publish(MQTT_STATUS_TOPIC, output.c_str());
        Serial.println("Published online status.");
        return true;
    } else {
        Serial.print("MQTT connection failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" ");
        return false;
    }
}

// Connect to WiFi - Returns true on success, false otherwise
bool connectToWiFi() {
    Serial.println("Connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    unsigned long wifiStartTime = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - wifiStartTime < 30000)) {
        Serial.print(".");
        delay(500);
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        return true;
    } else {
        Serial.println("\nWiFi connection failed!");
        WiFi.disconnect(true);
        delay(100);
        return false;
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\nESP32-CAM Face Detection Client");
    
    if (!mqttClient.setBufferSize(30000)) {
        Serial.println("Failed to set MQTT buffer size!");
    } else {
        Serial.println("MQTT buffer size set to 30000 bytes");
    }
    
    setupLEDs();
    
    if (!setupCamera()) {
        currentState = ERROR;
        lastStateChange = millis();
        Serial.println("Entering ERROR state due to camera init failure.");
        return;
    }
    
    currentState = WIFI_CONNECTING;
    lastStateChange = millis();
    Serial.println("State: WIFI_CONNECTING");
}

void loop() {
    unsigned long now = millis();
    updateLEDStatus();

    switch (currentState) {
        case WIFI_CONNECTING:
            if (connectToWiFi()) {
                currentState = MQTT_CONNECTING;
                lastStateChange = now;
                lastRetryAttempt = now;
                Serial.println("State: MQTT_CONNECTING");
            } else {
                Serial.println("WiFi failed, retrying after delay...");
                delay(RETRY_DELAY);
            }
            break;

        case MQTT_CONNECTING:
            if (now - lastRetryAttempt > RETRY_DELAY) {
                lastRetryAttempt = now;
                if (connectToMQTT()) {
                    currentState = READY;
                    lastStateChange = now;
                    Serial.println("State: READY");
                } else {
                    Serial.println("MQTT failed, will retry...");
                }
            }
            break;

        case READY:
            if (!mqttClient.connected()) {
                Serial.println("MQTT Disconnected!");
                currentState = MQTT_CONNECTING;
                lastStateChange = now;
                lastRetryAttempt = now;
                Serial.println("State: MQTT_CONNECTING");
            } else {
                mqttClient.loop();
                
                if (now - lastCaptureTime > CAPTURE_INTERVAL) {
                    lastCaptureTime = now;
                    captureAndPublishImage();
                }
            }
            break;

        case ERROR:
            Serial.println("State: ERROR - System halted. Restart required.");
            delay(10000);
            break;

        case INIT:
            currentState = WIFI_CONNECTING;
            lastStateChange = now;
            Serial.println("State: WIFI_CONNECTING (from INIT)");
            break;
    }
    
    delay(50);
}