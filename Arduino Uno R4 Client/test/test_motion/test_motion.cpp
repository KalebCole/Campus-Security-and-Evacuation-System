#include <Arduino.h>
#include <unity.h>
#include "../../test/test_helpers.h"
#include "../../src/config.h"

// Forward declarations
void handleMotion();

// Mock variables
StateMachine currentState = IDLE;
unsigned long lastMotionCheck = 0;
unsigned long mockMillis = 0;
bool mockMotionPin = false;

void setUp(void)
{
    // Reset all state
    currentState = IDLE;
    lastMotionCheck = 0;
    mockMillis = 0;
    mockMotionPin = false;
}

void test_motion_detection(void)
{
    // Setup
    currentState = IDLE;
    mockMotionPin = true; // HIGH = motion detected

    // Act
    handleMotion();

    // Assert
    TEST_ASSERT_EQUAL(ACTIVE_WAITING, currentState);
}

void test_motion_debounce(void)
{
    // Setup
    currentState = IDLE;
    mockMotionPin = true;
    lastMotionCheck = mockMillis;

    // Act - try to trigger before debounce time
    mockMillis += MOTION_DEBOUNCE - 1;
    handleMotion();

    // Assert - should not change state
    TEST_ASSERT_EQUAL(IDLE, currentState);

    // Act - try after debounce time
    mockMillis += 2; // Now past debounce time
    handleMotion();

    // Assert - should change state
    TEST_ASSERT_EQUAL(ACTIVE_WAITING, currentState);
}

void test_motion_clear(void)
{
    // Setup
    currentState = ACTIVE_WAITING;
    mockMotionPin = false; // No motion

    // Act
    handleMotion();

    // Assert
    TEST_ASSERT_EQUAL(IDLE, currentState);
}

void test_session_timeout(void)
{
    // Setup
    currentState = ACTIVE_SESSION;
    sessionStartTime = mockMillis;

    // Act - before timeout
    mockMillis += SESSION_TIMEOUT - 1;
    handleState();

    // Assert - should stay in session
    TEST_ASSERT_EQUAL(ACTIVE_SESSION, currentState);

    // Act - after timeout
    mockMillis += 2; // Now past timeout
    handleState();

    // Assert - should return to IDLE
    TEST_ASSERT_EQUAL(IDLE, currentState);
}

void setup()
{
    delay(2000); // Wait for Serial
    UNITY_BEGIN();

    RUN_TEST(test_motion_detection);
    RUN_TEST(test_motion_debounce);
    RUN_TEST(test_motion_clear);
    RUN_TEST(test_session_timeout);

    UNITY_END();
}

void loop() {}