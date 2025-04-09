#ifndef MQTT_H
#define MQTT_H

#include "esp_err.h"
#include "esp_camera.h"
#include "esp_mqtt_client.h"

// MQTT Topics
#define MQTT_TOPIC_STATUS "campus/security/status"
#define MQTT_TOPIC_SESSION "campus/security/session"
#define MQTT_TOPIC_AUTH "campus/security/auth"
#define MQTT_TOPIC_FACE "campus/security/face"

// MQTT Configuration
#define CONFIG_MQTT_BROKER_URI "mqtt://172.20.10.2:1883"
#define CONFIG_MQTT_CLIENT_ID "esp32cam_1"
#define CONFIG_MQTT_USERNAME "esp32cam"
#define CONFIG_MQTT_PASSWORD "your_password"

// Buffer Management
#define MQTT_MAX_PACKET_SIZE 30000  // Maximum MQTT packet size
#define MAX_IMAGE_SIZE (MQTT_MAX_PACKET_SIZE - 1024)  // Reserve 1KB for JSON metadata
#define MAX_SESSION_ID_LENGTH 32
#define MAX_JSON_BUFFER_SIZE 1024  // Maximum size for JSON payload (excluding image)

// Error codes
typedef enum {
    MQTT_OK = 0,
    MQTT_ERR_INVALID_ARG = -1,
    MQTT_ERR_IMAGE_TOO_LARGE = -2,
    MQTT_ERR_MEMORY = -3,
    MQTT_ERR_PUBLISH = -4,
    MQTT_ERR_NOT_CONNECTED = -5
} mqtt_err_t;

/**
 * @brief Initialize and start the MQTT client
 * 
 * @return esp_err_t ESP_OK on success, error code otherwise
 */
esp_err_t mqtt_app_start(void);

/**
 * @brief Publish a face detection result with image
 * 
 * @param fb Camera frame buffer containing the image
 * @param session_id Current session ID
 * @return mqtt_err_t MQTT_OK on success, error code otherwise
 */
mqtt_err_t mqtt_publish_face(camera_fb_t *fb, const char* session_id);

/**
 * @brief Request a new session ID from the server
 * 
 * @return mqtt_err_t MQTT_OK on success, error code otherwise
 */
mqtt_err_t mqtt_request_session(void);

/**
 * @brief Check the system status with the server
 * 
 * @return mqtt_err_t MQTT_OK on success, error code otherwise
 */
mqtt_err_t mqtt_check_system_status(void);

/**
 * @brief Check if MQTT client is connected
 * 
 * @return true if connected
 * @return false if not connected
 */
bool mqtt_is_connected(void);

/**
 * @brief Get the current MQTT error string
 * 
 * @param err Error code
 * @return const char* Error string
 */
const char* mqtt_err_to_str(mqtt_err_t err);

#endif /* MQTT_H */ 