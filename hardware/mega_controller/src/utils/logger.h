#ifndef LOGGER_H
#define LOGGER_H

#include <Arduino.h> // Include Arduino core for Serial, millis()

/**
 * @brief Logs a message to the Serial port with a timestamp and event tag.
 *
 * @param event A short string tag indicating the event type (e.g., "WIFI", "SENSOR").
 * @param message The message string to log.
 */
void log(const char *event, const char *message);

#endif // LOGGER_H