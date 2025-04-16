#ifndef LED_CONTROL_H
#define LED_CONTROL_H

#include <Arduino.h>
#include "../config.h"

// LED pin definition
#define LED_PIN 2   // Built-in LED (white LED next to the camera)
#define LED_FLASH 4 // Flash LED (larger LED on the back)

// Function declarations
void setupLEDs();
void blinkLED(int pin, int duration);
void updateLEDStatus(StateMachine currentState);

// External variable declarations
extern StateMachine currentState;
extern unsigned long lastStateChange;

#endif // LED_CONTROL_H
