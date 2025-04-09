#include "wifi_manager.hpp"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"

namespace campus::security::wifi
{

    WiFiManager::WiFiManager() : initialized_(false) {}

    WiFiManager::~WiFiManager()
    {
        deinit();
    }

    esp_err_t WiFiManager::init()
    {
        if (initialized_)
        {
            return ESP_OK;
        }

        ESP_ERROR_CHECK(esp_netif_init());
        ESP_ERROR_CHECK(esp_event_loop_create_default());
        esp_netif_create_default_wifi_sta();

        wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
        ESP_ERROR_CHECK(esp_wifi_init(&cfg));

        ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                            ESP_EVENT_ANY_ID,
                                                            &event_handler,
                                                            this,
                                                            NULL));
        ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                            IP_EVENT_STA_GOT_IP,
                                                            &event_handler,
                                                            this,
                                                            NULL));

        wifi_config_t wifi_config = {};
        strncpy((char *)wifi_config.sta.ssid, WIFI_SSID, sizeof(wifi_config.sta.ssid));
        strncpy((char *)wifi_config.sta.password, WIFI_PASSWORD, sizeof(wifi_config.sta.password));
        wifi_config.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
        wifi_config.sta.pmf_cfg.capable = true;
        wifi_config.sta.pmf_cfg.required = false;

        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
        ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
        ESP_ERROR_CHECK(esp_wifi_start());

        initialized_ = true;
        return ESP_OK;
    }

    esp_err_t WiFiManager::deinit()
    {
        if (!initialized_)
        {
            return ESP_OK;
        }

        ESP_ERROR_CHECK(esp_wifi_stop());
        ESP_ERROR_CHECK(esp_wifi_deinit());
        ESP_ERROR_CHECK(esp_event_loop_delete_default());
        esp_netif_deinit();

        initialized_ = false;
        return ESP_OK;
    }

    bool WiFiManager::is_connected() const
    {
        wifi_ap_record_t ap_info;
        return esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK;
    }

    std::string WiFiManager::get_ip_address() const
    {
        return ip_address_;
    }

    void WiFiManager::event_handler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data)
    {
        WiFiManager *manager = static_cast<WiFiManager *>(arg);

        if (event_base == WIFI_EVENT)
        {
            switch (event_id)
            {
            case WIFI_EVENT_STA_START:
                esp_wifi_connect();
                break;
            case WIFI_EVENT_STA_DISCONNECTED:
                ESP_LOGI(TAG, "WiFi disconnected, attempting to reconnect...");
                esp_wifi_connect();
                break;
            }
        }
        else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
        {
            ip_event_got_ip_t *event = static_cast<ip_event_got_ip_t *>(event_data);
            char ip_str[16];
            snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&event->ip_info.ip));
            manager->ip_address_ = ip_str;
            ESP_LOGI(TAG, "Got IP: %s", ip_str);
        }
    }

} // namespace campus::security::wifi