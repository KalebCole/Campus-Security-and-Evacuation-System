#include "led_control.h"

/**
 * Initialize LED pins
 */
void setupLEDs()
{
    pinMode(LED_PIN, OUTPUT);
    pinMode(LED_FLASH, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    digitalWrite(LED_FLASH, LOW);
}

/**
 * Blink an LED for the specified duration
 */
void blinkLED(int pin, int duration)
{
    digitalWrite(pin, HIGH);
    delay(duration);
    digitalWrite(pin, LOW);
    delay(duration);
}

/**
 * Update LED based on device state
 */
void updateLEDStatus(StateMachine currentState)
{
    switch (currentState)
    {
    case IDLE:
        // OFF in IDLE state
        digitalWrite(LED_PIN, LOW);
        break;
    case CONNECTING:
        // Slow blink (1000ms) for CONNECTING state
        digitalWrite(LED_PIN, (millis() / 1000) % 2);
        break;
    case FACE_DETECTING:
        // Normal blink (500ms) for FACE_DETECTING state
        digitalWrite(LED_PIN, (millis() / 500) % 2);
        break;
    case SESSION:
        // Very fast blink (100ms) for SESSION state
        digitalWrite(LED_PIN, (millis() / 100) % 2);
        break;
    case EMERGENCY:
        // Solid ON for EMERGENCY state
        digitalWrite(LED_PIN, HIGH);
        break;
    case ERROR:
        // Error pattern (very fast blink)
        digitalWrite(LED_PIN, (millis() / 100) % 2);
        break;
    default: // INIT or others
        // Solid OFF
        digitalWrite(LED_PIN, LOW);
        break;
    }
}
