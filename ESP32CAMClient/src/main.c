#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "camera.h"
#include "mqtt.h"
#include "wifi.h"

static const char *TAG = "main";

// State machine states
typedef enum {
    WAITING_FOR_MOTION, // TODO: see if I change it to INIT to sound better
    MOTION_DETECTED,
    CHECKING_SYSTEM,
    REQUESTING_SESSION,
    SESSION_READY,
    FACE_DETECTION,
    PUBLISHING_IMAGE,
    COOLDOWN,
    ERROR_STATE
} system_state_t;

// Global variables
static system_state_t current_state = WAITING_FOR_MOTION;
static char current_session_id[32] = {0};
static bool system_active = false;
static TaskHandle_t motion_task_handle = NULL;
static TaskHandle_t camera_task_handle = NULL;

// Motion detection task (simulated)
static void motion_detection_task(void *pvParameters)
{
    while (1) {
        // Simulate motion every 30 seconds
        vTaskDelay(pdMS_TO_TICKS(30000));
        
        if (current_state == WAITING_FOR_MOTION) {
            ESP_LOGI(TAG, "Motion detected!");
            current_state = MOTION_DETECTED;
        }
    }
}

// Camera task
static void camera_task(void *pvParameters)
{
    while (1) {
        switch (current_state) {
            case MOTION_DETECTED:
                if (camera_init() == ESP_OK) {
                    current_state = CHECKING_SYSTEM;
                } else {
                    current_state = ERROR_STATE;
                }
                break;

            case FACE_DETECTION:
                camera_fb_t *fb = camera_capture();
                if (fb) {
                    if (detect_faces(fb)) {
                        current_state = PUBLISHING_IMAGE;
                        mqtt_publish_face(fb, current_session_id);
                    }
                    camera_return_fb(fb);
                }
                vTaskDelay(pdMS_TO_TICKS(1000));
                break;

            default:
                vTaskDelay(pdMS_TO_TICKS(100));
                break;
        }
    }
}

// MQTT event handler
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;
    
    switch (event->event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT_EVENT_CONNECTED");
            mqtt_check_system_status();
            break;
            
        case MQTT_EVENT_DATA:
            ESP_LOGI(TAG, "MQTT_EVENT_DATA");
            if (strncmp(event->topic, MQTT_TOPIC_STATUS, event->topic_len) == 0) {
                system_active = (strncmp(event->data, "active", event->data_len) == 0);
                if (system_active && current_state == CHECKING_SYSTEM) {
                    current_state = REQUESTING_SESSION;
                    mqtt_request_session();
                }
            } else if (strncmp(event->topic, MQTT_TOPIC_SESSION, event->topic_len) == 0) {
                strncpy(current_session_id, event->data, event->data_len);
                current_session_id[event->data_len] = '\0';
                current_state = SESSION_READY;
            }
            break;
            
        default:
            break;
    }
}

void app_main(void)
{
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize WiFi
    ESP_ERROR_CHECK(wifi_init_sta());

    // Initialize MQTT
    ESP_ERROR_CHECK(mqtt_app_start());

    // Create tasks
    xTaskCreate(motion_detection_task, "motion_task", 4096, NULL, 5, &motion_task_handle);
    xTaskCreate(camera_task, "camera_task", 8192, NULL, 5, &camera_task_handle);

    // Main loop
    while (1) {
        switch (current_state) {
            case SESSION_READY:
                current_state = FACE_DETECTION;
                break;
                
            case ERROR_STATE:
                ESP_LOGE(TAG, "System in error state");
                vTaskDelay(pdMS_TO_TICKS(5000));
                break;
                
            default:
                vTaskDelay(pdMS_TO_TICKS(100));
                break;
        }
    }
}
