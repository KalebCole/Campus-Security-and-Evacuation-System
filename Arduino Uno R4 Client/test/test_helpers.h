#ifndef TEST_HELPERS_H
#define TEST_HELPERS_H

#include <Arduino.h>
#include <PubSubClient.h>
#include "../src/config.h"

// Mock variables
extern StateMachine currentState;
extern bool isEmergencyMode;
extern unsigned long lastRFIDCheck;
extern unsigned long lastMotionCheck;
extern unsigned long mockMillis;
extern bool mockMotionPin;
extern bool mockRFIDPin;
extern bool mockEmergencyPin;
extern bool mockUnlockPin;

// Mock time control
unsigned long millis() { return mockMillis; }

// Mock pin operations
void mockDigitalWrite(uint8_t pin, uint8_t val)
{
    if (pin == UNLOCK_PIN)
        mockUnlockPin = val;
}

// Override Arduino's digitalWrite
#define digitalWrite(pin, val) mockDigitalWrite(pin, val)

int mockDigitalRead(uint8_t pin)
{
    if (pin == MOTION_PIN)
        return mockMotionPin ? HIGH : LOW;
    if (pin == RFID_PIN)
        return mockRFIDPin ? HIGH : LOW;
    if (pin == EMERGENCY_PIN)
        return mockEmergencyPin ? HIGH : LOW;
    return LOW;
}

// Override Arduino's digitalRead
#define digitalRead(pin) mockDigitalRead(pin)

// Mock MQTT client
class MockMQTTClient
{
private:
    bool connected_state = false;
    char last_published_topic[64];
    char last_published_payload[256];
    bool publish_result = true;

public:
    void reset()
    {
        connected_state = false;
        last_published_topic[0] = '\0';
        last_published_payload[0] = '\0';
        publish_result = true;
    }

    bool connected() { return connected_state; }
    void setConnected(bool state) { connected_state = state; }

    bool publish(const char *topic, const char *payload)
    {
        strncpy(last_published_topic, topic, sizeof(last_published_topic) - 1);
        strncpy(last_published_payload, payload, sizeof(last_published_payload) - 1);
        return publish_result;
    }

    const char *getLastTopic() { return last_published_topic; }
    const char *getLastPayload() { return last_published_payload; }
    void setPublishResult(bool result) { publish_result = result; }
};

// Test assertions
#define TEST_ASSERT_MQTT_PUBLISHED(mock, topic) \
    TEST_ASSERT_EQUAL_STRING(topic, mock.getLastTopic())

#define TEST_ASSERT_MQTT_PAYLOAD_CONTAINS(mock, text) \
    TEST_ASSERT_TRUE(strstr(mock.getLastPayload(), text) != NULL)

// Mock RFID value generation
const char *generateMockRFID()
{
    static int currentIndex = 0;
    const char *rfid = MOCK_RFIDS[currentIndex];
    currentIndex = (currentIndex + 1) % NUM_MOCK_RFIDS;
    return rfid;
}

#endif // TEST_HELPERS_H