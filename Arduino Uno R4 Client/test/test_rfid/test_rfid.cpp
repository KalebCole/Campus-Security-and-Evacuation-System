#include <Arduino.h>
#include <unity.h>
#include "../../test/test_helpers.h"
#include "../../src/config.h"

// Forward declarations
void handleRFID();

// Mock variables
StateMachine currentState = IDLE;
bool isEmergencyMode = false;
unsigned long lastRFIDCheck = 0;
unsigned long mockMillis = 0;
bool mockRFIDPin = false;
bool mockUnlockPin = false;
MockMQTTClient mockMQTT;

void setUp(void)
{
    // Reset all state
    currentState = IDLE;
    isEmergencyMode = false;
    lastRFIDCheck = 0;
    mockMillis = 0;
    mockRFIDPin = false;
    mockUnlockPin = false;
    mockMQTT.reset();
}

void test_rfid_detection(void)
{
    // Setup
    currentState = ACTIVE_WAITING;
    mockRFIDPin = true; // HIGH = detected

    // Act
    handleRFID();

    // Assert
    TEST_ASSERT_EQUAL(ACTIVE_SESSION, currentState);
}

void test_rfid_debounce(void)
{
    // Setup
    currentState = ACTIVE_WAITING;
    mockRFIDPin = true;
    lastRFIDCheck = mockMillis;

    // Act - try to trigger before debounce time
    mockMillis += RFID_DEBOUNCE_TIME - 1;
    handleRFID();

    // Assert - should not change state
    TEST_ASSERT_EQUAL(ACTIVE_WAITING, currentState);

    // Act - try after debounce time
    mockMillis += 2; // Now past debounce time
    handleRFID();

    // Assert - should change state
    TEST_ASSERT_EQUAL(ACTIVE_SESSION, currentState);
}

void test_rfid_mqtt_message(void)
{
    // Setup
    currentState = ACTIVE_WAITING;
    mockRFIDPin = true;
    mockMQTT.setConnected(true);

    // Act
    handleRFID();

    // Assert
    TEST_ASSERT_MQTT_PUBLISHED(mockMQTT, TOPIC_RFID);
    TEST_ASSERT_MQTT_PAYLOAD_CONTAINS(mockMQTT, "device_id");
    TEST_ASSERT_MQTT_PAYLOAD_CONTAINS(mockMQTT, "rfid");
    TEST_ASSERT_MQTT_PAYLOAD_CONTAINS(mockMQTT, "timestamp");
}

void test_rfid_value_generation(void)
{
    // Setup
    currentState = ACTIVE_WAITING;
    mockRFIDPin = true;
    mockMQTT.setConnected(true);

    // Act
    handleRFID();

    // Assert - check that the generated RFID is one of our mock values
    bool foundValidRFID = false;
    for (int i = 0; i < NUM_MOCK_RFIDS; i++)
    {
        if (strstr(mockMQTT.getLastPayload(), MOCK_RFIDS[i]) != NULL)
        {
            foundValidRFID = true;
            break;
        }
    }
    TEST_ASSERT_TRUE(foundValidRFID);
}

void setup()
{
    delay(2000); // Wait for Serial
    UNITY_BEGIN();

    RUN_TEST(test_rfid_detection);
    RUN_TEST(test_rfid_debounce);
    RUN_TEST(test_rfid_mqtt_message);
    RUN_TEST(test_rfid_value_generation);

    UNITY_END();
}

void loop() {}