#include <Arduino.h>
#include <unity.h>
#include "../../test/test_helpers.h"
#include "../../src/config.h"

// Forward declarations
void handleEmergency();
void handleState();
void handleUnlock();

// Mock variables
StateMachine currentState = IDLE;
bool isEmergencyMode = false;
unsigned long mockMillis = 0;
bool mockEmergencyPin = false;
bool mockUnlockPin = false;
MockMQTTClient mockMQTT;

void setUp(void)
{
    // Reset all state
    currentState = IDLE;
    isEmergencyMode = false;
    mockMillis = 0;
    mockEmergencyPin = false;
    mockUnlockPin = false;
    mockMQTT.reset();
}

void test_emergency_trigger(void)
{
    // Setup
    currentState = ACTIVE_SESSION;
    mockEmergencyPin = true; // HIGH = emergency

    // Act
    handleState();

    // Assert
    TEST_ASSERT_EQUAL(EMERGENCY, currentState);
    TEST_ASSERT_TRUE(isEmergencyMode);
}

void test_emergency_override(void)
{
    // Test from each state
    StateMachine states[] = {IDLE, ACTIVE_WAITING, ACTIVE_SESSION};

    for (StateMachine state : states)
    {
        // Setup
        currentState = state;
        mockEmergencyPin = true;

        // Act
        handleState();

        // Assert
        TEST_ASSERT_EQUAL_MESSAGE(EMERGENCY, currentState,
                                  "Failed to override state");
    }
}

void test_emergency_mqtt(void)
{
    // Setup
    currentState = IDLE;
    mockEmergencyPin = true;
    mockMQTT.setConnected(true);

    // Act
    handleEmergency();

    // Assert
    TEST_ASSERT_MQTT_PUBLISHED(mockMQTT, TOPIC_EMERGENCY);
    TEST_ASSERT_MQTT_PAYLOAD_CONTAINS(mockMQTT, "emergency");
    TEST_ASSERT_MQTT_PAYLOAD_CONTAINS(mockMQTT, "unlock_triggered");
}

void test_emergency_unlock(void)
{
    // Setup
    currentState = IDLE;
    mockEmergencyPin = true;

    // Act
    handleEmergency();

    // Assert - should start unlock
    TEST_ASSERT_TRUE(mockUnlockPin);

    // Act - after unlock duration
    mockMillis += UNLOCK_SIGNAL_DURATION;
    handleUnlock();

    // Assert - should stop unlock
    TEST_ASSERT_FALSE(mockUnlockPin);
}

void test_emergency_timeout(void)
{
    // Setup
    currentState = EMERGENCY;
    emergencyStartTime = mockMillis;

    // Act - before timeout
    mockMillis += EMERGENCY_TIMEOUT_MS - 1;
    handleState();

    // Assert - should stay in emergency
    TEST_ASSERT_EQUAL(EMERGENCY, currentState);

    // Act - after timeout
    mockMillis += 2; // Now past timeout
    handleState();

    // Assert - should return to IDLE
    TEST_ASSERT_EQUAL(IDLE, currentState);
    TEST_ASSERT_FALSE(isEmergencyMode);
}

void setup()
{
    delay(2000); // Wait for Serial
    UNITY_BEGIN();

    RUN_TEST(test_emergency_trigger);
    RUN_TEST(test_emergency_override);
    RUN_TEST(test_emergency_mqtt);
    RUN_TEST(test_emergency_unlock);
    RUN_TEST(test_emergency_timeout);

    UNITY_END();
}

void loop() {}