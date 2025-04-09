#include "camera.h"
#include "esp_who.h"

static const char *TAG = "camera";

// Camera configuration
static camera_config_t camera_config = {
    .pin_pwdn = CAMERA_PIN_PWDN,
    .pin_reset = CAMERA_PIN_RESET,
    .pin_xclk = CAMERA_PIN_XCLK,
    .pin_sccb_sda = CAMERA_PIN_SIOD,
    .pin_sccb_scl = CAMERA_PIN_SIOC,
    .pin_d7 = CAMERA_PIN_D7,
    .pin_d6 = CAMERA_PIN_D6,
    .pin_d5 = CAMERA_PIN_D5,
    .pin_d4 = CAMERA_PIN_D4,
    .pin_d3 = CAMERA_PIN_D3,
    .pin_d2 = CAMERA_PIN_D2,
    .pin_d1 = CAMERA_PIN_D1,
    .pin_d0 = CAMERA_PIN_D0,
    .pin_vsync = CAMERA_PIN_VSYNC,
    .pin_href = CAMERA_PIN_HREF,
    .pin_pclk = CAMERA_PIN_PCLK,
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .pin_ledc_channel = LEDC_CHANNEL_0,
    .pixel_format = PIXFORMAT_JPEG,
    .frame_size = FRAMESIZE_QVGA,
    .jpeg_quality = 12,
    .fb_count = 1,
    .fb_location = CAMERA_FB_IN_PSRAM,
    .grab_mode = CAMERA_GRAB_WHEN_EMPTY
};

// ESP-WHO face detection
static who_face_detection_t face_detection;
static who_face_detection_config_t face_detection_config = {
    .min_face = 30,
    .max_face = 200,
    .face_scale = 1.1,
    .face_score = 0.5,
    .nms_threshold = 0.4
};

esp_err_t camera_init(void)
{
    esp_err_t err = esp_camera_init(&camera_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera Init Failed");
        return err;
    }

    // Initialize ESP-WHO face detection
    who_face_detection_init(&face_detection, &face_detection_config);

    // Configure camera settings
    sensor_t *s = esp_camera_sensor_get();
    s->set_vflip(s, 1);
    s->set_hmirror(s, 1);
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);
    s->set_aec_value(s, 300);
    s->set_gain_ctrl(s, 1);
    s->set_agc_gain(s, 0);
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
    s->set_lenc(s, 1);
    s->set_dcw(s, 1);
    s->set_colorbar(s, 0);

    ESP_LOGI(TAG, "Camera Init Success");
    return ESP_OK;
}

esp_err_t camera_deinit(void)
{
    esp_err_t err = esp_camera_deinit();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera Deinit Failed");
        return err;
    }
    return ESP_OK;
}

camera_fb_t* camera_capture(void)
{
    return esp_camera_fb_get();
}

void camera_return_fb(camera_fb_t* fb)
{
    esp_camera_fb_return(fb);
}

bool detect_faces(camera_fb_t* fb)
{
    if (!fb) return false;

    who_face_detection_result_t result;
    who_face_detection_run(&face_detection, fb->buf, fb->len, &result);

    if (result.num_faces > 0) {
        ESP_LOGI(TAG, "Face detected!");
        return true;
    }
    return false;
} 