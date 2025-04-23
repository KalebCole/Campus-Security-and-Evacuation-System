#ifndef CONFIG_H
#define CONFIG_H

// === Pin Definitions ===
#define EMERGENCY_TRIGGER_PIN 5 // Input pin receiving signal from Arduino Mega (Pin 4)
#define SERVO_PIN 9             // Output pin for the servo motor

// === Servo Parameters ===
#define SERVO_UNLOCK_ANGLE 95      // Angle in degrees for the unlocked position
#define SERVO_LOCK_ANGLE 180       // Angle in degrees for the locked position
#define SERVO_UNLOCK_TIMEOUT 15000 // Time in milliseconds to stay unlocked (15 seconds)

// === Serial Configuration ===

#define DEBUG_SERIAL_BAUD 115200 // Baud rate for Serial debugging

// WiFi Configuration
#define WIFI_SSID "iPod Mini"
#define WIFI_PASSWORD "H0t$p0t!"
#define WIFI_TIMEOUT 10000     // 10 seconds timeout
#define WIFI_ATTEMPT_DELAY 500 // 500ms between attempts

// MQTT Configuration
// TODO: update the mqtt broker address to the cloud broker on fly.io
// hostname assigned to it:         #define MQTT_BROKER "campus-security-evacuation-system.fly.dev"
// #define MQTT_BROKER "172.20.10.2"
// #define MQTT_PORT 1883
// EMQX MQTT Serverless Instance
#define MQTT_BROKER "z8002768.ala.us-east-1.emqxsl.com"
#define MQTT_PORT 8883
#define MQTT_CLIENT_ID "servo-arduino"

#define MQTT_BUFFER_SIZE 500

// MQTT Topics
#define TOPIC_UNLOCK "/unlock"       // Topic to receive unlock commands
#define TOPIC_EMERGENCY "/emergency" // Topic to publish emergency events

// EMQX CA Certificate (PEM Format)
const char* EMQX_CA_CERT_PEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDrzCCApegAwIBAgIQCDvgVpBCRrGhdWrJWZHHSjANBgkqhkiG9w0BAQUFADBh
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBD
QTAeFw0wNjExMTAwMDAwMDBaFw0zMTExMTAwMDAwMDBaMGExCzAJBgNVBAYTAlVT
MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j
b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IENBMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4jvhEXLeqKTTo1eqUKKPC3eQyaKl7hLOllsB
CSDMAZOnTjC3U/dDxGkAV53ijSLdhwZAAIEJzs4bg7/fzTtxRuLWZscFs3YnFo97
nh6Vfe63SKMI2tavegw5BmV/Sl0fvBf4q77uKNd0f3p4mVmFaG5cIzJLv07A6Fpt
43C/dxC//AH2hdmoRBBYMql1GNXRor5H4idq9Joz+EkIYIvUX7Q6hL+hqkpMfT7P
T19sdl6gSzeRntwi5m3OFBqOasv+zbMUZBfHWymeMr/y7vrTC0LUq7dBMtoM1O/4
gdW7jVg/tRvoSSiicNoxBN33shbyTApOB6jtSj1etX+jkMOvJwIDAQABo2MwYTAO
BgNVHQ8BAf8EBAMCAYYwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUA95QNVbR
TLtm8KPiGxvDl7I90VUwHwYDVR0jBBgwFoAUA95QNVbRTLtm8KPiGxvDl7I90VUw
DQYJKoZIhvcNAQEFBQADggEBAMucN6pIExIK+t1EnE9SsPTfrgT1eXkIoyQY/Esr
hMAtudXH/vTBH1jLuG2cenTnmCmrEbXjcKChzUyImZOMkXDiqw8cvpOp/2PV5Adg
06O/nVsJ8dWO41P0jmP6P6fbtGbfYmbW0W5BjfIttep3Sp+dWOIrWcBAI+0tKIJF
PnlUkiaY4IBIqDfv8NZ5YBberOgOzW6sRBc4L0na4UU+Krk2U886UAb3LujEV0ls
YSEY1QSteDwsOoBrp+uvFRTp2InBuThs4pFsiv9kuXclVzDAGySj4dzp30d8tbQk
CAUw7C29C79Fv1C5qfPrmAESrciIxpg0X40KPMbp1ZWVbd4=
-----END CERTIFICATE-----
)EOF";

// --- Deprecated/Consolidated --- Keep only needed defines
// #define SERVO_LOCKED_POSITION 180 // Duplicate of SERVO_LOCK_ANGLE
// #define SERVO_UNLOCKED_POSITION 95 // Duplicate of SERVO_UNLOCK_ANGLE

#endif // CONFIG_H