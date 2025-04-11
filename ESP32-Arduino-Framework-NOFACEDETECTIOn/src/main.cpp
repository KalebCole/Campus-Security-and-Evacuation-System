#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <esp_camera.h>
#include <ArduinoJson.h>
#include <base64.hpp>
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

// MQTT client objects
WiFiClient espClient;
PubSubClient mqttClient(espClient);

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

  case ACTIVE_WAITING:
    if (now - lastLedToggle >= LED_NORMAL_BLINK)
    {
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState);
      lastLedToggle = now;
    }
    break;

  case ACTIVE_SESSION:
    if (now - lastLedToggle >= LED_SESSION_BLINK)
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

// MQTT Callback function
void mqttCallback(char *topic, byte *payload, unsigned int length)
{
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++)
  {
    Serial.print((char)payload[i]);
  }
  Serial.println();

  // Handle emergency messages
  if (strcmp(topic, TOPIC_EMERGENCY) == 0)
  {
    currentState = EMERGENCY;
    lastStateChange = millis();
    Serial.println("Emergency mode activated!");
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
    mqttClient.publish(TOPIC_STATUS, output.c_str());
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

void setup()
{
  Serial.begin(115200);
  delay(1000);
  Serial.println("\nESP32-CAM Security System");

  if (!mqttClient.setBufferSize(MQTT_BUFFER_SIZE))
  {
    Serial.println("Failed to set MQTT buffer size!");
  }
  else
  {
    Serial.println("MQTT buffer size set to 30000 bytes");
  }

  setupLEDs();

  if (!setupCamera())
  {
    currentState = ERROR;
    lastStateChange = millis();
    Serial.println("Entering ERROR state due to camera init failure.");
    return;
  }

  currentState = IDLE;
  lastStateChange = millis();
  Serial.println("State: IDLE");
}

void loop()
{
  updateLEDStatus();
  unsigned long now = millis();

  // Basic state machine implementation
  switch (currentState)
  {
  case IDLE:
    if (WiFi.status() != WL_CONNECTED)
    {
      if (connectToWiFi())
      {
        if (connectToMQTT())
        {
          currentState = ACTIVE_WAITING;
          lastStateChange = now;
        }
      }
    }
    break;

  case ACTIVE_WAITING:
    if (!mqttClient.connected())
    {
      if (now - lastRetryAttempt > RETRY_DELAY)
      {
        lastRetryAttempt = now;
        if (!connectToMQTT())
        {
          currentState = ERROR;
          lastStateChange = now;
        }
      }
    }
    else
    {
      mqttClient.loop();
    }
    break;

  case ACTIVE_SESSION:
    if (!mqttClient.connected())
    {
      currentState = ERROR;
      lastStateChange = now;
    }
    else
    {
      mqttClient.loop();
      // TODO: Add image capture and processing
    }
    break;

  case EMERGENCY:
    if (now - lastStateChange >= EMERGENCY_TIMEOUT)
    {
      currentState = IDLE;
      lastStateChange = now;
    }
    break;

  case ERROR:
    if (now - lastRetryAttempt > RETRY_DELAY)
    {
      lastRetryAttempt = now;
      if (connectToWiFi() && connectToMQTT())
      {
        currentState = IDLE;
        lastStateChange = now;
      }
    }
    break;
  }

  delay(50);
}