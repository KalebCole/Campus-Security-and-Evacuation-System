#ifndef CAMERA_H
#define CAMERA_H

#include "esp_camera.h"
#include "esp_log.h"
#include "esp_err.h"

// Camera configuration
// TODO: see if this matches what the ESP32CAM is using

/*
This is what the ESP32CAM is using from working CPP example:


#define LED_PIN 2  // Built-in LED (white LED next to the camera)
#define LED_FLASH 4  // Flash LED (larger LED on the back)

// Camera Pin Definitions based on working MicroPython example
#define PWDN_GPIO_NUM     -1 // From MicroPython example
#define RESET_GPIO_NUM    -1 // NC
#define XCLK_GPIO_NUM     21 // From MicroPython example
#define SIOD_GPIO_NUM     26 // SDA - Matches MicroPython
#define SIOC_GPIO_NUM     27 // SCL - Matches MicroPython

// Data pins from MicroPython d0-d7 sequence
#define Y2_GPIO_NUM        4 // D0 from MicroPython
#define Y3_GPIO_NUM        5 // D1 from MicroPython
#define Y4_GPIO_NUM       18 // D2 from MicroPython
#define Y5_GPIO_NUM       19 // D3 from MicroPython
#define Y6_GPIO_NUM       36 // D4 from MicroPython
#define Y7_GPIO_NUM       39 // D5 from MicroPython
#define Y8_GPIO_NUM       34 // D6 from MicroPython
#define Y9_GPIO_NUM       35 // D7 from MicroPython

// Control pins - Match MicroPython
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

*/

#define CAMERA_PIN_PWDN     -1
#define CAMERA_PIN_RESET    -1
#define CAMERA_PIN_XCLK     21
#define CAMERA_PIN_SIOD     26
#define CAMERA_PIN_SIOC     27
#define CAMERA_PIN_D7       35
#define CAMERA_PIN_D6       34
#define CAMERA_PIN_D5       39
#define CAMERA_PIN_D4       36
#define CAMERA_PIN_D3       19
#define CAMERA_PIN_D2       18
#define CAMERA_PIN_D1        5
#define CAMERA_PIN_D0        4
#define CAMERA_PIN_VSYNC    25
#define CAMERA_PIN_HREF     23
#define CAMERA_PIN_PCLK     22

// Function declarations
esp_err_t camera_init(void);
esp_err_t camera_deinit(void);
camera_fb_t* camera_capture(void);
void camera_return_fb(camera_fb_t* fb);
bool detect_faces(camera_fb_t* fb);

#endif // CAMERA_H 