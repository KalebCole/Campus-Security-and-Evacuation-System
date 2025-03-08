#include <Arduino.h>
#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
// Resource:
// 1. https://www.elithecomputerguy.com/2019/07/write-post-data-to-server-with-arduino-uno-with-wifi/

// Constants
const bool TEST_MODE = false;   // Set to false for normal operation
const bool RFID_MOCK = true;    // Set to true to use mock RFID database
const int TEST_INTERVAL = 3000; // Test every 3 seconds
const int RFID_PIN = 2;         // RFID reader pins

// WiFi debugging constants
const bool WIFI_DEBUG = true;          // Enable detailed WiFi debugging
const int WIFI_CHECK_INTERVAL = 30000; // Check WiFi status every 30 seconds
const int MAX_WIFI_RETRIES = 5;        // Maximum number of reconnection attempts
unsigned long lastWifiCheck = 0;       // Last time WiFi status was checked

// LED blink patterns
const int WIFI_CONNECTING_BLINK = 100; // Fast blink while connecting
const int WIFI_CONNECTED_BLINK = 2000; // Slow blink when connected
const int WIFI_ERROR_BLINK = 300;      // Medium fast blink on error

// WIFI Constants for Kaleb's Mobile Hotspot
const char *ssid = "iPod Mini";
const char *password = "H0t$p0t!";

// Create a WifiClient object to connect to the server
WiFiClient wifi;
// Add server connection details
const char *server = "172.20.10.2"; // ip on the mobile hotspot
const int port = 5000;
HttpClient client = HttpClient(wifi, server, port);

// Session management (optional - if you want to maintain session across requests)
String currentSessionId = "";

// RFID database (mock)
const String RFID_DATABASE[] = {
    "123456", // Bob
    "654321", // Rob
    "789012"  // Charlie
};

// sizeof(RFID_DATABASE) gives you the total size in bytes of the entire array
// sizeof(RFID_DATABASE[0]) gives you the size in bytes of a single element
// Dividing the total size by the size of one element gives you the number of elements
const int NUM_RFIDS = sizeof(RFID_DATABASE) / sizeof(RFID_DATABASE[0]);

// put function declarations here:
void printWifiStatus();
void connectToWifi();
void checkWifiStatus();
void blinkLED(int blinkRate, int numBlinks);
void wifiStatusLED();
String getRandomRFID();


String getRandomRFID();
void triggerRFID(int pinNumber);
String makeRFIDPostRequest(String rfid);
void sendRFIDPostRequest(String rfid);

// Function to print detailed WiFi status information
void printWifiStatus()
{
  Serial.println("\n--------- WiFi Status ---------");

  // Connection status
  int status = WiFi.status();
  Serial.print("Status: ");
  switch (status)
  {
  case WL_CONNECTED:
    Serial.println("CONNECTED");
    break;
  case WL_NO_SHIELD:
    Serial.println("NO SHIELD");
    break;
  case WL_IDLE_STATUS:
    Serial.println("IDLE");
    break;
  case WL_NO_SSID_AVAIL:
    Serial.println("NO SSID AVAILABLE");
    break;
  case WL_SCAN_COMPLETED:
    Serial.println("SCAN COMPLETED");
    break;
  case WL_CONNECT_FAILED:
    Serial.println("CONNECTION FAILED");
    break;
  case WL_CONNECTION_LOST:
    Serial.println("CONNECTION LOST");
    break;
  case WL_DISCONNECTED:
    Serial.println("DISCONNECTED");
    break;
  default:
    Serial.println("UNKNOWN");
    break;
  }

  // print the SSID of the network you're attached to:
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  // print your WiFi shield's IP address:
  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);

  // print your MAC address:
  byte mac[6];
  WiFi.macAddress(mac);
  Serial.print("MAC Address: ");
  for (int i = 0; i < 6; i++)
  {
    Serial.print(mac[i], HEX);
    if (i < 5)
      Serial.print(":");
  }
  Serial.println();

  // print the received signal strength:
  long rssi = WiFi.RSSI();
  Serial.print("Signal Strength (RSSI): ");
  Serial.print(rssi);
  Serial.print(" dBm (");

  // Convert RSSI to percentage (roughly)
  int quality = 2 * (rssi + 100);
  if (quality > 100)
    quality = 100;
  if (quality < 0)
    quality = 0;
  Serial.print(quality);
  Serial.println("%)");

  // print encryption type
  byte encryption = WiFi.encryptionType();
  Serial.print("Encryption Type: ");
  switch (encryption)
  {
  case 2:
    Serial.println("TKIP (WPA)");
    break;
  case 5:
    Serial.println("WEP");
    break;
  case 4:
    Serial.println("CCMP (WPA2)");
    break;
  case 7:
    Serial.println("NONE");
    break;
  case 8:
    Serial.println("AUTO");
    break;
  default:
    Serial.println("UNKNOWN");
    break;
  }

  Serial.println("-------------------------------");
}

// Function to connect to WiFi with improved error handling and debugging
void connectToWifi()
{
  Serial.println("\nAttempting to connect to WiFi network...");
  Serial.print("SSID: ");
  Serial.println(ssid);

  // First, disconnect if already connected
  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("Disconnecting from previous WiFi connection...");
    WiFi.disconnect();
    delay(1000);
  }

  // Begin connection attempt
  WiFi.begin(ssid, password);

  // Wait for connection with timeout and visual feedback
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED)
  {
    blinkLED(WIFI_CONNECTING_BLINK, 1); // Blink rapidly during connection attempt
    Serial.print(".");
    attempts++;

    // Check if we've reached maximum attempts
    if (attempts >= MAX_WIFI_RETRIES * 3)
    { // 3 blinks per retry
      Serial.println("\nFailed to connect to WiFi after multiple attempts.");
      Serial.print("Last Status: ");
      switch (WiFi.status())
      {
      case WL_NO_SHIELD:
        Serial.println("NO SHIELD");
        break;
      case WL_IDLE_STATUS:
        Serial.println("IDLE");
        break;
      case WL_NO_SSID_AVAIL:
        Serial.println("NO SSID AVAILABLE - Check if network is in range");
        break;
      case WL_SCAN_COMPLETED:
        Serial.println("SCAN COMPLETED");
        break;
      case WL_CONNECT_FAILED:
        Serial.println("CONNECTION FAILED - Check password");
        break;
      case WL_CONNECTION_LOST:
        Serial.println("CONNECTION LOST");
        break;
      case WL_DISCONNECTED:
        Serial.println("DISCONNECTED");
        break;
      default:
        Serial.println("UNKNOWN ERROR");
        break;
      }

      // Indicate error with LED pattern
      blinkLED(WIFI_ERROR_BLINK, 5);
      return;
    }
  }

  Serial.println("\nConnected to WiFi successfully!");
  blinkLED(WIFI_CONNECTED_BLINK, 3); // Slow blinks indicate successful connection
  printWifiStatus();
}

// Function to periodically check WiFi status
void checkWifiStatus()
{
  unsigned long currentMillis = millis();

  // Check if it's time to verify WiFi status
  if (currentMillis - lastWifiCheck >= WIFI_CHECK_INTERVAL)
  {
    lastWifiCheck = currentMillis;

    if (WiFi.status() != WL_CONNECTED)
    {
      Serial.println("WiFi connection lost! Attempting to reconnect...");
      connectToWifi();
    }
    else if (WIFI_DEBUG)
    {
      Serial.println("WiFi connection still active.");
      // Only print full status every 3 checks to avoid console spam
      static int checkCount = 0;
      checkCount++;
      if (checkCount >= 3)
      {
        printWifiStatus();
        checkCount = 0;
      }
      else
      {
        // Just print RSSI for a quick check
        Serial.print("Signal strength (RSSI): ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");
      }
    }
  }
}

// Function to blink LED at a specific rate and number of times
void blinkLED(int blinkRate, int numBlinks)
{
  for (int i = 0; i < numBlinks; i++)
  {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(blinkRate / 2);
    digitalWrite(LED_BUILTIN, LOW);
    delay(blinkRate / 2);
  }
}

// Function to visually indicate WiFi status with LED
void wifiStatusLED()
{
  switch (WiFi.status())
  {
  case WL_CONNECTED:
    // Connected - one long blink
    digitalWrite(LED_BUILTIN, HIGH);
    delay(200);
    digitalWrite(LED_BUILTIN, LOW);
    break;
  case WL_DISCONNECTED:
  case WL_CONNECTION_LOST:
    // Disconnected - two fast blinks
    for (int i = 0; i < 2; i++)
    {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(100);
      digitalWrite(LED_BUILTIN, LOW);
      delay(100);
    }
    break;
  default:
    // Other states - three very fast blinks
    for (int i = 0; i < 3; i++)
    {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(50);
      digitalWrite(LED_BUILTIN, LOW);
      delay(50);
    }
    break;
  }
}

String getRandomRFID()
{
  // Generate a random index between 0 and NUM_RFIDS
  int randomIndex = random(0, NUM_RFIDS);
  return RFID_DATABASE[randomIndex];
}

// Function to take in a high signal on a pin and trigger a random selection of an rfid tag from a mock database
void triggerRFID(int pinNumber)
{
  if (RFID_MOCK)
  {
    sendRFIDPostRequest(getRandomRFID());
    return;
  }
  // Check if the pin is high
  if (digitalRead(pinNumber) == HIGH)
    sendRFIDPostRequest(getRandomRFID());
  {
  }
};

// function to take in an rfid string and form it into a post request to the server
String makeRFIDPostRequest(String rfid)
{
  // Create a JSON payload with the RFID tag
  String jsonBody = "{\"rfid_tag\":\"" + rfid + "\"";

  // Add session_id if we already have one
  if (currentSessionId.length() > 0)
  {
    jsonBody += ",\"session_id\":\"" + currentSessionId + "\"";
  }

  jsonBody += "}";

  Serial.println("JSON Payload: " + jsonBody);
  return jsonBody;
}

void sendRFIDPostRequest(String rfid)
{
  Serial.println("\nSending RFID POST request for tag: " + rfid);

  // Make a POST request to the server
  String rfidPostData = makeRFIDPostRequest(rfid);

  Serial.println("Connecting to server: " + String(server) + ":" + String(port));

  // Begin the request
  client.beginRequest();

  // Set the endpoint
  client.post("/api/rfid");

  // Set the headers
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", rfidPostData.length());

  // Send the body
  client.beginBody();
  client.print(rfidPostData);

  // Complete the request
  client.endRequest();

  // Read the response status code
  int statusCode = client.responseStatusCode();
  Serial.print("Response Status Code: ");
  Serial.println(statusCode);

  // Read the response body
  String response = client.responseBody();
  Serial.print("Response Body: ");
  Serial.println(response);

  // Check if we got a session ID in the response
  if (statusCode == 202)
  { // 202 Accepted
    // Try to extract session_id from response json
    int sessionIdIndex = response.indexOf("\"session_id\":\"");
    if (sessionIdIndex > 0)
    {
      sessionIdIndex += 13; // Length of "session_id":"
      int sessionIdEndIndex = response.indexOf("\"", sessionIdIndex);
      currentSessionId = response.substring(sessionIdIndex, sessionIdEndIndex);
      Serial.print("Saved session ID: ");
      Serial.println(currentSessionId);
    }
  }
  else if (statusCode != 200)
  {
    Serial.println("POST request failed!");
    // If we got an error, clear the session ID
    currentSessionId = "";
    // Visual indication of error
    blinkLED(WIFI_ERROR_BLINK, 3);
  }
  else
  {
    Serial.println("Request successful!");
    // Visual indication of success
    blinkLED(50, 1);
  }
}

void setup()
{
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(RFID_PIN, INPUT); // TODO: does this need to be a pullup?

  // initialize serial communication
  Serial.begin(9600);

  // Wait for Serial to be ready (for debugging)
  // Timeout after 5 seconds to allow operation without serial monitor
  unsigned long startTime = millis();
  while (!Serial && (millis() - startTime < 5000))
    ;

  Serial.println("\n\n=== Arduino Uno R4 WiFi RFID Client ===");
  Serial.println("Starting up...");

  // Fast blink 3 times to indicate boot sequence
  blinkLED(200, 3);

  // Properly initialize random number generator
  randomSeed(analogRead(0));

  // Connect to WiFi network with visual feedback
  connectToWifi();

  Serial.println("Setup complete! Running main loop...");
}

void loop()
{
  // Check WiFi status periodically
  checkWifiStatus();

  // Visual indicator of current WiFi status every few seconds
  static unsigned long lastLedUpdate = 0;
  if (millis() - lastLedUpdate > 5000)
  {
    wifiStatusLED();
    lastLedUpdate = millis();
  }

  // Test mode functionality
  if (TEST_MODE)
  {
    Serial.println("TEST MODE: Simulating RFID scan...");
    String rfid = getRandomRFID();
    Serial.print("Simulated RFID tag: ");
    Serial.println(rfid);
    triggerRFID(RFID_PIN);
    delay(TEST_INTERVAL);
  }

  // Regular RFID checking
  triggerRFID(RFID_PIN);
}