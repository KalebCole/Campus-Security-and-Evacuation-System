#include "logger.h"

// Simple logging helper
void log(const char *event, const char *message)
{
    // Check if Serial is available before trying to print
    if (Serial)
    {
        Serial.print("[");
        Serial.print(millis());
        Serial.print("] [");
        Serial.print(event);
        Serial.print("] ");
        Serial.println(message);
    }
}