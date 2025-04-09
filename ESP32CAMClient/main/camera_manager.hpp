#pragma once

#include <memory>
#include <esp_camera.h>
#include "human_face_detect.hpp"
#include "who_cam.hpp"

namespace campus::security::cam
{

    class CameraManager
    {
    public:
        CameraManager();
        ~CameraManager();

        esp_err_t init();
        esp_err_t deinit();
        bool detect_faces(camera_fb_t *fb);
        camera_fb_t *capture_frame();
        void return_frame(camera_fb_t *fb);

    private:
        std::unique_ptr<dl::detect::HumanFaceDetect> face_detector_;
        std::unique_ptr<who::cam::WhoCam> camera_;
        bool initialized_;

        esp_err_t configure_camera();
    };

} // namespace campus::security::cam