#ifndef WIFI_H
#define WIFI_H

#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"

// WiFi configuration
#define WIFI_SSID "iPod Mini"
#define WIFI_PASS "H0t$p0t!"
#define MAXIMUM_RETRY 5

// Function declarations
esp_err_t wifi_init_sta(void);
bool wifi_is_connected(void);
void wifi_stop(void);

#endif // WIFI_H 