#pragma once

#include <string>
#include <esp_wifi.h>
#include <esp_event.h>

namespace campus::security::wifi
{

    class WiFiManager
    {
    public:
        WiFiManager();
        ~WiFiManager();

        esp_err_t init();
        esp_err_t deinit();
        bool is_connected() const;
        std::string get_ip_address() const;

    private:
        static void event_handler(void *arg, esp_event_base_t event_base, int32_t event_id, void *event_data);

        bool initialized_;
        std::string ip_address_;

        static constexpr const char *TAG = "wifi_manager";
        static constexpr const char *WIFI_SSID = "iPod Mini";
        static constexpr const char *WIFI_PASSWORD = "H0t$p0t!";
    };

} // namespace campus::security::wifi