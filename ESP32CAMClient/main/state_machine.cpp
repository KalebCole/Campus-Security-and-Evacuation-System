#include "state_machine.hpp"
#include "esp_log.h"

namespace campus::security::state
{

    StateMachine::StateMachine(std::shared_ptr<cam::CameraManager> camera,
                               std::shared_ptr<mqtt::MQTTManager> mqtt,
                               std::shared_ptr<wifi::WiFiManager> wifi)
        : camera_(camera),
          mqtt_(mqtt),
          wifi_(wifi),
          current_state_(State::WAITING_FOR_MOTION),
          system_active_(false),
          running_(false),
          motion_task_handle_(nullptr),
          camera_task_handle_(nullptr) {}

    StateMachine::~StateMachine()
    {
        stop();
    }

    void StateMachine::run()
    {
        if (running_)
        {
            return;
        }

        running_ = true;

        // Create motion detection task
        xTaskCreate([](void *arg)
                    { static_cast<StateMachine *>(arg)->motion_detection_task(); }, "motion_task", 4096, this, 5, &motion_task_handle_);

        // Create camera task
        xTaskCreate([](void *arg)
                    { static_cast<StateMachine *>(arg)->camera_task(); }, "camera_task", 8192, this, 5, &camera_task_handle_);
    }

    void StateMachine::stop()
    {
        if (!running_)
        {
            return;
        }

        running_ = false;

        if (motion_task_handle_)
        {
            vTaskDelete(motion_task_handle_);
            motion_task_handle_ = nullptr;
        }

        if (camera_task_handle_)
        {
            vTaskDelete(camera_task_handle_);
            camera_task_handle_ = nullptr;
        }
    }

    void StateMachine::motion_detection_task()
    {
        while (running_)
        {
            if (current_state_ == State::WAITING_FOR_MOTION)
            {
                // Simulate motion detection
                ESP_LOGI(TAG, "Motion detected!");
                current_state_ = State::MOTION_DETECTED;
            }
            vTaskDelay(pdMS_TO_TICKS(MOTION_CHECK_INTERVAL_MS));
        }
    }

    void StateMachine::camera_task()
    {
        while (running_)
        {
            switch (current_state_)
            {
            case State::MOTION_DETECTED:
                if (camera_->init() == ESP_OK)
                {
                    current_state_ = State::CHECKING_SYSTEM;
                }
                else
                {
                    current_state_ = State::ERROR_STATE;
                }
                break;

            case State::FACE_DETECTION:
            {
                camera_fb_t *fb = camera_->capture_frame();
                if (fb)
                {
                    if (camera_->detect_faces(fb))
                    {
                        current_state_ = State::PUBLISHING_IMAGE;
                        mqtt_->publish_face(fb, session_id_);
                    }
                    camera_->return_frame(fb);
                }
                break;
            }

            case State::ERROR_STATE:
                ESP_LOGE(TAG, "System in error state");
                vTaskDelay(pdMS_TO_TICKS(5000));
                break;

            default:
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(CAMERA_CHECK_INTERVAL_MS));
        }
    }

} // namespace campus::security::state