#include "mqtt.h"
#include "esp_log.h"
#include "esp_mqtt_client.h"
#include "esp_event.h"
#include "esp_timer.h"
#include "cJSON.h"
#include "base64.h"

static const char *TAG = "mqtt";
static esp_mqtt_client_handle_t client = NULL;

// MQTT event handler
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;
    
    switch (event->event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");
            esp_mqtt_client_subscribe(client, MQTT_TOPIC_STATUS, 0);
            esp_mqtt_client_subscribe(client, MQTT_TOPIC_SESSION, 0);
            esp_mqtt_client_subscribe(client, MQTT_TOPIC_AUTH, 0);
            break;
            
        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "MQTT_EVENT_DISCONNECTED");
            break;
            
        case MQTT_EVENT_SUBSCRIBED:
            ESP_LOGI(TAG, "MQTT_EVENT_SUBSCRIBED");
            break;
            
        case MQTT_EVENT_UNSUBSCRIBED:
            ESP_LOGI(TAG, "MQTT_EVENT_UNSUBSCRIBED");
            break;
            
        case MQTT_EVENT_PUBLISHED:
            ESP_LOGI(TAG, "MQTT_EVENT_PUBLISHED");
            break;
            
        case MQTT_EVENT_DATA:
            ESP_LOGI(TAG, "MQTT_EVENT_DATA");
            break;
            
        case MQTT_EVENT_ERROR:
            ESP_LOGI(TAG, "MQTT_EVENT_ERROR");
            break;
            
        default:
            break;
    }
}

esp_err_t mqtt_app_start(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .uri = CONFIG_MQTT_BROKER_URI,
        .client_id = CONFIG_MQTT_CLIENT_ID,
        .username = CONFIG_MQTT_USERNAME,
        .password = CONFIG_MQTT_PASSWORD,
    };

    client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(client);

    return ESP_OK;
}

mqtt_err_t mqtt_publish_face(camera_fb_t *fb, const char* session_id)
{
    if (!client || !fb) return MQTT_ERR_INVALID_ARG;
    if (!mqtt_is_connected()) return MQTT_ERR_NOT_CONNECTED;
    if (fb->len > MAX_IMAGE_SIZE) return MQTT_ERR_IMAGE_TOO_LARGE;
    if (strlen(session_id) > MAX_SESSION_ID_LENGTH) return MQTT_ERR_INVALID_ARG;

    // Create JSON payload
    cJSON *root = cJSON_CreateObject();
    if (!root) return MQTT_ERR_MEMORY;
    
    cJSON_AddStringToObject(root, "device_id", CONFIG_MQTT_CLIENT_ID);
    cJSON_AddStringToObject(root, "session_id", session_id);
    cJSON_AddNumberToObject(root, "timestamp", esp_timer_get_time() / 1000);
    cJSON_AddStringToObject(root, "format", "jpeg");
    cJSON_AddTrueToObject(root, "face_detected");
    
    // Base64 encode image
    char *base64_image = NULL;
    size_t base64_len = 0;
    esp_base64_encode(NULL, 0, &base64_len, fb->buf, fb->len);
    if (base64_len > MAX_JSON_BUFFER_SIZE) {
        cJSON_Delete(root);
        return MQTT_ERR_IMAGE_TOO_LARGE;
    }
    
    base64_image = malloc(base64_len);
    if (!base64_image) {
        cJSON_Delete(root);
        return MQTT_ERR_MEMORY;
    }
    
    esp_base64_encode(base64_image, base64_len, &base64_len, fb->buf, fb->len);
    cJSON_AddStringToObject(root, "image", base64_image);
    
    // Convert to string
    char *payload = cJSON_PrintUnformatted(root);
    if (!payload) {
        free(base64_image);
        cJSON_Delete(root);
        return MQTT_ERR_MEMORY;
    }
    
    size_t payload_len = strlen(payload);
    if (payload_len > MQTT_MAX_PACKET_SIZE) {
        free(payload);
        free(base64_image);
        cJSON_Delete(root);
        return MQTT_ERR_IMAGE_TOO_LARGE;
    }
    
    // Publish
    int msg_id = esp_mqtt_client_publish(client, MQTT_TOPIC_FACE, payload, payload_len, 0, 0);
    if (msg_id < 0) {
        free(payload);
        free(base64_image);
        cJSON_Delete(root);
        return MQTT_ERR_PUBLISH;
    }
    
    // Cleanup
    free(base64_image);
    free(payload);
    cJSON_Delete(root);
    
    return MQTT_OK;
}

mqtt_err_t mqtt_request_session(void)
{
    if (!client) return MQTT_ERR_INVALID_ARG;
    if (!mqtt_is_connected()) return MQTT_ERR_NOT_CONNECTED;

    cJSON *root = cJSON_CreateObject();
    if (!root) return MQTT_ERR_MEMORY;
    
    cJSON_AddStringToObject(root, "device_id", CONFIG_MQTT_CLIENT_ID);
    cJSON_AddStringToObject(root, "action", "request_session");
    
    char *payload = cJSON_PrintUnformatted(root);
    if (!payload) {
        cJSON_Delete(root);
        return MQTT_ERR_MEMORY;
    }
    
    size_t payload_len = strlen(payload);
    int msg_id = esp_mqtt_client_publish(client, MQTT_TOPIC_SESSION, payload, payload_len, 0, 0);
    
    free(payload);
    cJSON_Delete(root);
    
    return (msg_id < 0) ? MQTT_ERR_PUBLISH : MQTT_OK;
}

mqtt_err_t mqtt_check_system_status(void)
{
    if (!client) return MQTT_ERR_INVALID_ARG;
    if (!mqtt_is_connected()) return MQTT_ERR_NOT_CONNECTED;

    cJSON *root = cJSON_CreateObject();
    if (!root) return MQTT_ERR_MEMORY;
    
    cJSON_AddStringToObject(root, "device_id", CONFIG_MQTT_CLIENT_ID);
    cJSON_AddStringToObject(root, "action", "status_check");
    
    char *payload = cJSON_PrintUnformatted(root);
    if (!payload) {
        cJSON_Delete(root);
        return MQTT_ERR_MEMORY;
    }
    
    size_t payload_len = strlen(payload);
    int msg_id = esp_mqtt_client_publish(client, MQTT_TOPIC_STATUS, payload, payload_len, 0, 0);
    
    free(payload);
    cJSON_Delete(root);
    
    return (msg_id < 0) ? MQTT_ERR_PUBLISH : MQTT_OK;
}

bool mqtt_is_connected(void)
{
    return client != NULL && esp_mqtt_client_is_connected(client);
}

const char* mqtt_err_to_str(mqtt_err_t err)
{
    switch (err) {
        case MQTT_OK:
            return "Success";
        case MQTT_ERR_INVALID_ARG:
            return "Invalid argument";
        case MQTT_ERR_IMAGE_TOO_LARGE:
            return "Image too large for MQTT packet";
        case MQTT_ERR_MEMORY:
            return "Memory allocation failed";
        case MQTT_ERR_PUBLISH:
            return "Failed to publish message";
        case MQTT_ERR_NOT_CONNECTED:
            return "MQTT client not connected";
        default:
            return "Unknown error";
    }
} 