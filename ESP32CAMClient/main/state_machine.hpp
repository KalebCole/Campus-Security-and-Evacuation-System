#pragma once

#include <memory>
#include <string>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "camera_manager.hpp"
#include "mqtt_manager.hpp"
#include "wifi_manager.hpp"

namespace campus::security::state
{

    enum class State
    {
        WAITING_FOR_MOTION,
        MOTION_DETECTED,
        CHECKING_SYSTEM,
        REQUESTING_SESSION,
        SESSION_READY,
        FACE_DETECTION,
        PUBLISHING_IMAGE,
        COOLDOWN,
        ERROR_STATE
    };

    class StateMachine
    {
    public:
        StateMachine(std::shared_ptr<cam::CameraManager> camera,
                     std::shared_ptr<mqtt::MQTTManager> mqtt,
                     std::shared_ptr<wifi::WiFiManager> wifi);
        ~StateMachine();

        void run();
        void stop();

    private:
        void motion_detection_task();
        void camera_task();
        void handle_state_transition();

        std::shared_ptr<cam::CameraManager> camera_;
        std::shared_ptr<mqtt::MQTTManager> mqtt_;
        std::shared_ptr<wifi::WiFiManager> wifi_;

        State current_state_;
        std::string session_id_;
        bool system_active_;
        bool running_;

        TaskHandle_t motion_task_handle_;
        TaskHandle_t camera_task_handle_;

        static constexpr const char *TAG = "state_machine";
        static constexpr uint32_t MOTION_CHECK_INTERVAL_MS = 30000;
        static constexpr uint32_t CAMERA_CHECK_INTERVAL_MS = 1000;
    };

} // namespace campus::security::state