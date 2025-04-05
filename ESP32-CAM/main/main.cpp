#include <esp_who.h>
#include <esp_camera.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <base64.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// MQTT settings
const char* MQTT_BROKER = "YOUR_MQTT_BROKER_IP";
const int MQTT_PORT = 1883;
const char* MQTT_TOPIC = "campus/security/face";
const char* MQTT_STATUS_TOPIC = "campus/security/status";
const char* MQTT_AUTH_TOPIC = "campus/security/auth";
const char* DEVICE_ID = "esp32cam_1";
const char* DEVICE_SECRET = "YOUR_DEVICE_SECRET";

// LED pins
#define LED_BUILTIN 33
#define LED_STATUS 4

// Camera pins for ESP32-CAM
#define CAMERA_MODEL_AI_THINKER
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// State machine states
enum DeviceState {
    INIT,
    WIFI_CONNECTING,
    MQTT_CONNECTING,
    AUTHENTICATING,
    READY,
    ERROR,
    EMERGENCY_STOP
};

// Current state
DeviceState currentState = INIT;

// MQTT client
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// ESP-WHO face detection
who_face_detection_t face_detection;
who_face_detection_config_t face_detection_config;

// System status
bool systemActive = false;
unsigned long lastStatusCheck = 0;
const unsigned long STATUS_CHECK_INTERVAL = 30000; // 30 seconds

// MQTT retry settings
const int MAX_MQTT_RETRIES = 5;
int mqttRetryCount = 0;
const unsigned long MQTT_RETRY_DELAY = 5000; // 5 seconds
unsigned long lastMqttRetry = 0;

// LED patterns
const int LED_PATTERN_INIT = 100; // Fast blink
const int LED_PATTERN_WIFI = 500; // Medium blink
const int LED_PATTERN_MQTT = 1000; // Slow blink
const int LED_PATTERN_READY = 2000; // Very slow blink
const int LED_PATTERN_ERROR = 200; // Fast double blink
const int LED_PATTERN_EMERGENCY = 100; // Very fast blink

void setupCamera() {
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
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_GRAYSCALE;
    config.frame_size = FRAMESIZE_QVGA;  // 320x240
    config.jpeg_quality = 12;
    config.fb_count = 1;

    // Initialize camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x", err);
        return;
    }

    // Configure ESP-WHO face detection
    face_detection_config.min_face = 30;
    face_detection_config.max_face = 200;
    face_detection_config.face_scale = 1.1;
    face_detection_config.face_score = 0.5;
    face_detection_config.nms_threshold = 0.4;

    who_face_detection_init(&face_detection, &face_detection_config);
}

void connectWiFi() {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("WiFi connected");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    String message = String((char*)payload).substring(0, length);
    
    if (String(topic) == MQTT_AUTH_TOPIC) {
        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, message);
        
        if (!error && doc["device_id"] == DEVICE_ID) {
            if (doc["status"] == "authenticated") {
                currentState = READY;
                systemActive = true;
            } else {
                currentState = ERROR;
                systemActive = false;
            }
        }
    } else if (String(topic) == MQTT_STATUS_TOPIC) {
        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, message);
        
        if (!error && doc["status"] == "emergency_stop") {
            currentState = EMERGENCY_STOP;
            systemActive = false;
        }
    }
}

void connectMQTT() {
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
    
    while (!mqttClient.connected()) {
        if (mqttClient.connect(DEVICE_ID)) {
            Serial.println("MQTT connected");
            mqttClient.subscribe(MQTT_AUTH_TOPIC);
            mqttClient.subscribe(MQTT_STATUS_TOPIC);
            authenticateDevice();
        } else {
            delay(5000);
        }
    }
}

void authenticateDevice() {
    StaticJsonDocument<200> doc;
    doc["device_id"] = DEVICE_ID;
    doc["secret"] = DEVICE_SECRET;
    
    String payload;
    serializeJson(doc, payload);
    
    mqttClient.publish(MQTT_AUTH_TOPIC, payload.c_str());
}

void checkSystemStatus() {
    if (millis() - lastStatusCheck > STATUS_CHECK_INTERVAL) {
        lastStatusCheck = millis();
        
        StaticJsonDocument<200> doc;
        doc["device_id"] = DEVICE_ID;
        doc["status"] = "check";
        
        String payload;
        serializeJson(doc, payload);
        
        mqttClient.publish(MQTT_STATUS_TOPIC, payload.c_str());
    }
}

void updateLED() {
    static unsigned long lastLEDUpdate = 0;
    static bool ledState = false;
    
    if (millis() - lastLEDUpdate > getLEDPattern()) {
        lastLEDUpdate = millis();
        ledState = !ledState;
        digitalWrite(LED_STATUS, ledState);
    }
}

int getLEDPattern() {
    switch (currentState) {
        case INIT:
            return LED_PATTERN_INIT;
        case WIFI_CONNECTING:
            return LED_PATTERN_WIFI;
        case MQTT_CONNECTING:
        case AUTHENTICATING:
            return LED_PATTERN_MQTT;
        case READY:
            return LED_PATTERN_READY;
        case ERROR:
            return LED_PATTERN_ERROR;
        case EMERGENCY_STOP:
            return LED_PATTERN_EMERGENCY;
        default:
            return LED_PATTERN_ERROR;
    }
}

void processAndPublishFace(camera_fb_t* fb) {
    if (!systemActive || currentState != READY) {
        return;
    }
    
    // Detect faces
    who_face_detection_result_t result;
    // the parameters are the following:
    // 1. the face detection struct
    // 2. the image buffer
    // 3. the image buffer length
    // 4. the result struct
    who_face_detection_run(&face_detection, fb->buf, fb->len, &result);

    if (result.num_faces > 0) {
        // Process each detected face
        for (int i = 0; i < result.num_faces; i++) {
            // Extract face region
            uint8_t* face_data = result.faces[i].data;
            size_t face_size = result.faces[i].size;

            // Create MQTT payload
            String payload = "{";
            payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
            payload += "\"timestamp\":\"" + String(millis()) + "\",";
            payload += "\"image\":\"" + base64::encode(face_data, face_size) + "\",";
            payload += "\"format\":\"jpg\"";
            payload += "}";

            // Publish to MQTT
            mqttClient.publish(MQTT_TOPIC, payload.c_str());
        }
    }
}

void setup() {
    Serial.begin(115200);
    
    // Initialize LEDs
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(LED_STATUS, OUTPUT);
    
    // Initialize components
    setupCamera();
    currentState = WIFI_CONNECTING;
    connectWiFi();
    
    currentState = MQTT_CONNECTING;
    connectMQTT();
}

void loop() {
    // Update LED status
    updateLED();
    
    // Maintain MQTT connection
    if (!mqttClient.connected() && currentState != EMERGENCY_STOP) {
        if (millis() - lastMqttRetry > MQTT_RETRY_DELAY) {
            lastMqttRetry = millis();
            mqttRetryCount++;
            
            if (mqttRetryCount <= MAX_MQTT_RETRIES) {
                currentState = MQTT_CONNECTING;
                connectMQTT();
            } else {
                currentState = ERROR;
            }
        }
    } else {
        mqttClient.loop();
    }
    
    // Check system status
    if (currentState == READY) {
        checkSystemStatus();
    }
    
    // Process camera frames
    if (currentState == READY && systemActive) {
        camera_fb_t* fb = esp_camera_fb_get();
        if (fb) {
            processAndPublishFace(fb);
            esp_camera_fb_return(fb);
        }
    }
    
    // Small delay to prevent overwhelming the system
    delay(100);
} 