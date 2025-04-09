#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "camera_manager.hpp"
#include "mqtt_manager.hpp"
#include "wifi_manager.hpp"
#include "state_machine.hpp"

using namespace campus::security;

static const char *TAG = "main";

extern "C" void app_main(void)
{
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
    {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize components
    auto wifi_manager = std::make_unique<wifi::WiFiManager>();
    auto mqtt_manager = std::make_unique<mqtt::MQTTManager>();
    auto camera_manager = std::make_unique<cam::CameraManager>();
    auto state_machine = std::make_unique<state::StateMachine>();

    // Initialize WiFi
    ESP_ERROR_CHECK(wifi_manager->init());

    // Initialize MQTT
    ESP_ERROR_CHECK(mqtt_manager->init());

    // Initialize Camera
    ESP_ERROR_CHECK(camera_manager->init());

    // Start state machine
    state_machine->run();

    // Keep the main task alive
    while (true)
    {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}