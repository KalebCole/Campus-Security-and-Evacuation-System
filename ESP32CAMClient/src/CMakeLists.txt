# This file was automatically generated for projects
# without default 'CMakeLists.txt' file.

FILE(GLOB_RECURSE app_sources ${CMAKE_SOURCE_DIR}/src/*.*)

idf_component_register(
    SRCS 
        "main.c"
        "camera.c"
        "mqtt.c"
        "wifi.c"
    INCLUDE_DIRS 
        "include"
    REQUIRES 
        esp32-camera
        esp-who
        esp_http_client
        esp_https_ota
        nvs_flash
        esp_wifi
        esp_mqtt_client
        driver
        esp_event
        esp_log
        esp_timer
)
