#include <Arduino.h>
#include "config.h"

// --- Configuration ---
// Control whether debouncing logic is active (1) or simple reads are used (0)
#define USE_DEBOUNCING 1

// --- Global Variables ---

// Emergency State Tracking
bool emergencyActive = false;   // Is the emergency currently active?
int stableEmergencyState = LOW; // Assuming INPUT, LOW is idle
#if USE_DEBOUNCING
int lastRawEmergencyState = LOW;
unsigned long lastEmergencyDebounceTime = 0;
#endif

// Motion State Tracking
int stableMotionState = LOW; // Assuming starts LOW
#if USE_DEBOUNCING
int lastRawMotionState = LOW;
unsigned long lastMotionDebounceTime = 0;
#endif
int prevStableMotionState = LOW; // To log only actual changes

// RFID State Tracking (from integration test)
bool rfidSignalActive = false;         // Is the RFID output signal (Pin 9) currently HIGH?
unsigned long lastRfidPinHighTime = 0; // Timestamp of the last time Pin 6 read HIGH

void setup()
{
    // 1. Initialize Debug Serial (Serial Monitor via USB)
    Serial.begin(DEBUG_SERIAL_BAUD);
    while (!Serial)
        ;
    Serial.println(F("\n--- Arduino Mega GPIO Hub Initializing ---"));

    // 2. Print Pin Configuration
    Serial.println(F("Pin Configuration:"));
    Serial.print(F("  Input - Motion: "));
    Serial.println(MOTION_INPUT_PIN);
    Serial.print(F("  Input - RFID: "));
    Serial.println(RFID_INPUT_PIN);
    Serial.print(F("  Input - Emergency: "));
    Serial.println(EMERGENCY_PIN);
    Serial.print(F("  Output - Motion Signal (ESP32): "));
    Serial.println(MOTION_SIGNAL_OUTPUT_PIN);
    Serial.print(F("  Output - RFID Signal (ESP32): "));
    Serial.println(RFID_SIGNAL_OUTPUT_PIN);
    Serial.print(F("  Output - Servo Trigger (Uno): "));
    Serial.println(SERVO_TRIGGER_OUT_PIN);

    // 3. Initialize Pin Modes
    pinMode(MOTION_INPUT_PIN, INPUT);
    pinMode(RFID_INPUT_PIN, INPUT);
    pinMode(EMERGENCY_PIN, INPUT);

    pinMode(MOTION_SIGNAL_OUTPUT_PIN, OUTPUT);
    pinMode(RFID_SIGNAL_OUTPUT_PIN, OUTPUT);
    pinMode(SERVO_TRIGGER_OUT_PIN, OUTPUT);

    // 4. Initialize Output Pins LOW
    digitalWrite(MOTION_SIGNAL_OUTPUT_PIN, LOW);
    digitalWrite(RFID_SIGNAL_OUTPUT_PIN, LOW);
    digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
    Serial.println(F("Outputs initialized LOW."));

    // 5. Initialize Stable States
    stableMotionState = digitalRead(MOTION_INPUT_PIN);
    stableEmergencyState = digitalRead(EMERGENCY_PIN);
    prevStableMotionState = stableMotionState; // Init previous state tracking
#if USE_DEBOUNCING
    lastRawMotionState = stableMotionState;
    lastRawEmergencyState = stableEmergencyState;
#endif

    Serial.println(F("--- Setup Complete ---"));
}

void loop()
{
    unsigned long currentTime = millis();

    // --- 1. Handle Emergency Input (Highest Priority) ---
#if USE_DEBOUNCING
    int currentRawEmergency = digitalRead(EMERGENCY_PIN);
    // If state changed, reset debounce timer
    if (currentRawEmergency != lastRawEmergencyState)
    {
        lastEmergencyDebounceTime = currentTime;
    }
    // If state has been stable for long enough
    if ((currentTime - lastEmergencyDebounceTime) > SENSOR_DEBOUNCE_TIME_MS)
    {
        // If the stable state needs updating
        if (currentRawEmergency != stableEmergencyState)
        {
            Serial.print("Emergency pin stable state changed: ");
            Serial.print(stableEmergencyState);
            Serial.print(" -> ");
            Serial.println(currentRawEmergency);
            stableEmergencyState = currentRawEmergency;
            // Action is handled below based on stableEmergencyState
        }
    }
    lastRawEmergencyState = currentRawEmergency;
#else // Simple direct read if debouncing is disabled
    int currentEmergencyRead = digitalRead(EMERGENCY_PIN);
    if (currentEmergencyRead != stableEmergencyState)
    {
        Serial.printf("Emergency pin state changed (direct read): %d -> %d\n", stableEmergencyState, currentEmergencyRead);
        stableEmergencyState = currentEmergencyRead;
        // Action is handled below
    }
#endif

    // Check current stable emergency state for activation/deactivation
    if (stableEmergencyState == HIGH && !emergencyActive)
    {
        emergencyActive = true;
        Serial.println(F("***** EMERGENCY DETECTED *****"));
        Serial.println(F("  -> Triggering Servo Pulse for Uno..."));
        digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
        delay(SERVO_TRIGGER_DURATION_MS); // Keep pin LOW for specified duration
        digitalWrite(SERVO_TRIGGER_OUT_PIN, HIGH);
        Serial.println(F("  -> Servo Pulse Complete."));

        // Ensure  are forced LOW during emergency
        digitalWrite(MOTION_SIGNAL_OUTPUT_PIN, LOW);
        digitalWrite(RFID_SIGNAL_OUTPUT_PIN, LOW);
        rfidSignalActive = false;    // Reset RFID output state too
        prevStableMotionState = LOW; // Ensure motion logs correctly on release
        Serial.println(F("  -> Motion/RFID Signals to ESP32 Forced LOW."));
    }
    else if (stableEmergencyState == LOW && emergencyActive)
    {
        emergencyActive = false;
        Serial.println(F("--- Emergency Released ---"));
        // added this to turn off the servo trigger pin
        digitalWrite(SERVO_TRIGGER_OUT_PIN, LOW);
    }

    // --- 2. Handle Motion & RFID ONLY if NO emergency is active ---
    if (!emergencyActive)
    {
        // --- Handle Motion Sensor ---
#if USE_DEBOUNCING
        int currentRawMotion = digitalRead(MOTION_INPUT_PIN);
        // If state changed, reset debounce timer
        if (currentRawMotion != lastRawMotionState)
        {
            lastMotionDebounceTime = currentTime;
        }
        // If state has been stable for long enough
        if ((currentTime - lastMotionDebounceTime) > SENSOR_DEBOUNCE_TIME_MS)
        {
            // If the stable state needs updating
            if (currentRawMotion != stableMotionState)
            {
                // Log only actual changes to stable state
                Serial.print("Motion pin stable state changed: ");
                Serial.print(stableMotionState);
                Serial.print(" -> ");
                Serial.println(currentRawMotion);
                stableMotionState = currentRawMotion;
            }
        }
        lastRawMotionState = currentRawMotion;
#else // Simple direct read if debouncing is disabled
        int currentMotionRead = digitalRead(MOTION_INPUT_PIN);
        if (currentMotionRead != stableMotionState)
        {
            Serial.printf("Motion pin state changed (direct read): %d -> %d\n", stableMotionState, currentMotionRead);
            stableMotionState = currentMotionRead;
        }
#endif
        // Update output based on stable state, log only if output actually changes
        if (stableMotionState != prevStableMotionState)
        {
            digitalWrite(MOTION_SIGNAL_OUTPUT_PIN, stableMotionState);
            Serial.print(F("  -> Motion Output (Pin 8) set to: "));
            Serial.println(stableMotionState == HIGH ? "HIGH" : "LOW");
            prevStableMotionState = stableMotionState; // Update tracker
        }

        // --- Handle RFID Sensor (Activity Timeout Logic from integration test) ---
        int currentRfidInputState = digitalRead(RFID_INPUT_PIN);

        if (currentRfidInputState == HIGH)
        {
            // Pin 6 is HIGH - this means activity is present or ongoing
            lastRfidPinHighTime = currentTime; // Keep resetting the timeout timer

            if (!rfidSignalActive)
            {
                // If output signal wasn't already active, turn it on
                Serial.println(F("-> RFID Input (Pin 6) HIGH, Activating Output (Pin 9)"));
                digitalWrite(RFID_SIGNAL_OUTPUT_PIN, HIGH);
                rfidSignalActive = true;
            }
            // else: Input is HIGH, Output is already HIGH - do nothing
        }
        else // currentRfidInputState is LOW
        {
            if (rfidSignalActive)
            {
                // Only check for timeout if the output signal was previously active
                if (currentTime - lastRfidPinHighTime >= RFID_ACTIVITY_TIMEOUT_MS)
                {
                    // Timeout expired - pin 6 has been LOW for long enough
                    Serial.println(F("-> RFID Input (Pin 6) Timeout, Deactivating Output (Pin 9)"));
                    digitalWrite(RFID_SIGNAL_OUTPUT_PIN, LOW);
                    rfidSignalActive = false;
                }
                // else - it's LOW, but the timeout hasn't expired yet - do nothing
            }
            // else - it's LOW and output was already inactive - do nothing
        }

    } // End of if(!emergencyActive)

    // Small delay to prevent busy-waiting and allow loop to yield
    delay(10);
}
