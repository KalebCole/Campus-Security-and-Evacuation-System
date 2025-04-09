#include "camera_manager.hpp"
#include "esp_log.h"

namespace campus::security::cam
{

    static const char *TAG = "camera_manager";

    CameraManager::CameraManager() : initialized_(false) {}

    CameraManager::~CameraManager()
    {
        deinit();
    }

    esp_err_t CameraManager::init()
    {
        if (initialized_)
        {
            return ESP_OK;
        }

        esp_err_t err = configure_camera();
        if (err != ESP_OK)
        {
            ESP_LOGE(TAG, "Failed to configure camera");
            return err;
        }

        face_detector_ = std::make_unique<dl::detect::HumanFaceDetect>();
        camera_ = std::make_unique<who::cam::WhoCam>();

        initialized_ = true;
        return ESP_OK;
    }

    esp_err_t CameraManager::deinit()
    {
        if (!initialized_)
        {
            return ESP_OK;
        }

        face_detector_.reset();
        camera_.reset();
        initialized_ = false;
        return ESP_OK;
    }

    esp_err_t CameraManager::configure_camera()
    {
        camera_config_t config = {
            .pin_pwdn = -1,
            .pin_reset = -1,
            .pin_xclk = 21,
            .pin_sscb_sda = 26,
            .pin_sscb_scl = 27,
            .pin_d7 = 35,
            .pin_d6 = 34,
            .pin_d5 = 39,
            .pin_d4 = 36,
            .pin_d3 = 19,
            .pin_d2 = 18,
            .pin_d1 = 5,
            .pin_d0 = 4,
            .pin_vsync = 25,
            .pin_href = 23,
            .pin_pclk = 22,
            .xclk_freq_hz = 20000000,
            .ledc_timer = LEDC_TIMER_0,
            .ledc_channel = LEDC_CHANNEL_0,
            .pixel_format = PIXFORMAT_JPEG,
            .frame_size = FRAMESIZE_VGA,
            .jpeg_quality = 12,
            .fb_count = 1,
            .grab_mode = CAMERA_GRAB_WHEN_EMPTY};

        return esp_camera_init(&config);
    }

    bool CameraManager::detect_faces(camera_fb_t *fb)
    {
        if (!initialized_ || !fb)
        {
            return false;
        }
        return face_detector_->detect(fb);
    }

    camera_fb_t *CameraManager::capture_frame()
    {
        if (!initialized_)
        {
            return nullptr;
        }
        return esp_camera_fb_get();
    }

    void CameraManager::return_frame(camera_fb_t *fb)
    {
        if (fb)
        {
            esp_camera_fb_return(fb);
        }
    }

} // namespace campus::security::cam