#pragma once

#include <memory>
#include <string>
#include <esp_mqtt_client.h>
#include "esp_camera.h"

namespace campus::security::mqtt
{

    class MQTTManager
    {
    public:
        MQTTManager();
        ~MQTTManager();

        esp_err_t init();
        esp_err_t deinit();
        bool is_connected() const;
        esp_err_t publish_face(camera_fb_t *fb, const std::string &session_id);
        esp_err_t request_session();
        esp_err_t check_system_status();

    private:
        static void event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data);

        esp_mqtt_client_handle_t client_;
        bool initialized_;
        std::string session_id_;

        static constexpr const char *TAG = "mqtt_manager";
        static constexpr const char *TOPIC_STATUS = "campus/security/status";
        static constexpr const char *TOPIC_SESSION = "campus/security/session";
        static constexpr const char *TOPIC_AUTH = "campus/security/auth";
        static constexpr const char *TOPIC_FACE = "campus/security/face";
    };

} // namespace campus::security::mqtt