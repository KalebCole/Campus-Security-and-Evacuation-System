#include "mqtt_manager.hpp"
#include "esp_log.h"
#include "cJSON.h"
#include "base64.h"

namespace campus::security::mqtt
{

    MQTTManager::MQTTManager() : client_(nullptr), initialized_(false) {}

    MQTTManager::~MQTTManager()
    {
        deinit();
    }

    esp_err_t MQTTManager::init()
    {
        if (initialized_)
        {
            return ESP_OK;
        }

        esp_mqtt_client_config_t mqtt_cfg = {
            .uri = "mqtt://172.20.10.2:1883",
            .client_id = "esp32cam_1",
            .username = "esp32cam",
            .password = "your_password"};

        client_ = esp_mqtt_client_init(&mqtt_cfg);
        if (!client_)
        {
            ESP_LOGE(TAG, "Failed to initialize MQTT client");
            return ESP_FAIL;
        }

        esp_mqtt_client_register_event(client_, ESP_EVENT_ANY_ID, event_handler, this);
        esp_mqtt_client_start(client_);

        initialized_ = true;
        return ESP_OK;
    }

    esp_err_t MQTTManager::deinit()
    {
        if (!initialized_)
        {
            return ESP_OK;
        }

        if (client_)
        {
            esp_mqtt_client_stop(client_);
            esp_mqtt_client_destroy(client_);
            client_ = nullptr;
        }

        initialized_ = false;
        return ESP_OK;
    }

    bool MQTTManager::is_connected() const
    {
        return client_ && esp_mqtt_client_is_connected(client_);
    }

    esp_err_t MQTTManager::publish_face(camera_fb_t *fb, const std::string &session_id)
    {
        if (!is_connected() || !fb)
        {
            return ESP_FAIL;
        }

        cJSON *root = cJSON_CreateObject();
        if (!root)
        {
            return ESP_ERR_NO_MEM;
        }

        cJSON_AddStringToObject(root, "device_id", "esp32cam_1");
        cJSON_AddStringToObject(root, "session_id", session_id.c_str());
        cJSON_AddNumberToObject(root, "timestamp", esp_timer_get_time() / 1000);
        cJSON_AddStringToObject(root, "format", "jpeg");
        cJSON_AddTrueToObject(root, "face_detected");

        char *base64_image = nullptr;
        size_t base64_len = 0;
        esp_base64_encode(nullptr, 0, &base64_len, fb->buf, fb->len);
        base64_image = (char *)malloc(base64_len);
        if (!base64_image)
        {
            cJSON_Delete(root);
            return ESP_ERR_NO_MEM;
        }

        esp_base64_encode(base64_image, base64_len, &base64_len, fb->buf, fb->len);
        cJSON_AddStringToObject(root, "image", base64_image);

        char *payload = cJSON_PrintUnformatted(root);
        if (!payload)
        {
            free(base64_image);
            cJSON_Delete(root);
            return ESP_ERR_NO_MEM;
        }

        int msg_id = esp_mqtt_client_publish(client_, TOPIC_FACE, payload, strlen(payload), 0, 0);

        free(base64_image);
        free(payload);
        cJSON_Delete(root);

        return (msg_id < 0) ? ESP_FAIL : ESP_OK;
    }

    esp_err_t MQTTManager::request_session()
    {
        if (!is_connected())
        {
            return ESP_FAIL;
        }

        cJSON *root = cJSON_CreateObject();
        if (!root)
        {
            return ESP_ERR_NO_MEM;
        }

        cJSON_AddStringToObject(root, "device_id", "esp32cam_1");
        cJSON_AddStringToObject(root, "action", "request_session");

        char *payload = cJSON_PrintUnformatted(root);
        if (!payload)
        {
            cJSON_Delete(root);
            return ESP_ERR_NO_MEM;
        }

        int msg_id = esp_mqtt_client_publish(client_, TOPIC_SESSION, payload, strlen(payload), 0, 0);

        free(payload);
        cJSON_Delete(root);

        return (msg_id < 0) ? ESP_FAIL : ESP_OK;
    }

    esp_err_t MQTTManager::check_system_status()
    {
        if (!is_connected())
        {
            return ESP_FAIL;
        }

        cJSON *root = cJSON_CreateObject();
        if (!root)
        {
            return ESP_ERR_NO_MEM;
        }

        cJSON_AddStringToObject(root, "device_id", "esp32cam_1");
        cJSON_AddStringToObject(root, "action", "status_check");

        char *payload = cJSON_PrintUnformatted(root);
        if (!payload)
        {
            cJSON_Delete(root);
            return ESP_ERR_NO_MEM;
        }

        int msg_id = esp_mqtt_client_publish(client_, TOPIC_STATUS, payload, strlen(payload), 0, 0);

        free(payload);
        cJSON_Delete(root);

        return (msg_id < 0) ? ESP_FAIL : ESP_OK;
    }

    void MQTTManager::event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
    {
        MQTTManager *manager = static_cast<MQTTManager *>(handler_args);
        esp_mqtt_event_handle_t event = static_cast<esp_mqtt_event_handle_t>(event_data);

        switch (event->event_id)
        {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");
            esp_mqtt_client_subscribe(manager->client_, TOPIC_STATUS, 0);
            esp_mqtt_client_subscribe(manager->client_, TOPIC_SESSION, 0);
            esp_mqtt_client_subscribe(manager->client_, TOPIC_AUTH, 0);
            break;

        case MQTT_EVENT_DATA:
            ESP_LOGI(TAG, "MQTT_EVENT_DATA");
            // Handle incoming messages
            break;

        default:
            break;
        }
    }

} // namespace campus::security::mqtt