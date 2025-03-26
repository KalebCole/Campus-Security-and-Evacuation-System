#include <Arduino.h>
#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
// Resource:
// 1. https://www.elithecomputerguy.com/2019/07/write-post-data-to-server-with-arduino-uno-with-wifi/

// Constants
const bool TEST_MODE = false; // Set to false for normal operation
const bool RFID_MOCK = true;  // Set to true to use mock RFID database
const int RFID_PIN = 2;       // RFID reader pins

// System activity constants
bool systemActive = false;
const int SYSTEM_CHECK_INTERVAL = 10000; // Check system status every 10 seconds
const int ACTIVATION_DELAY = 2000;       // Wait 2 seconds after activation before sending RFID
unsigned long lastSystemCheck = 0;       // Last time system status was checked
unsigned long systemActivationTime = 0;  // When the system was last activated

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

// Current session ID for RFID processs
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

// Define state machine for RFID process
enum ProcessState
{
  IDLE,
  CHECKING_SYSTEM,
  REQUESTING_SESSION,
  SESSION_READY,
  SENDING_RFID,
  COOLDOWN
};

// Current state in the RFID process
ProcessState currentState = IDLE;

// Timing variables
unsigned long stateStartTime = 0;
const int STATE_TIMEOUT = 10000;  // 10 seconds timeout for any state
const int COOLDOWN_PERIOD = 5000; // 5 seconds between complete cycles

// Session management
bool sessionValid = false;
const int SESSION_RETRY_INTERVAL = 10000; // 10 seconds between session retries
unsigned long lastSessionRequestTime = 0;

// ----------------
// Function Prototypes
// ----------------

// WIFI
void printWifiStatus();
void connectToWifi();
void checkWifiStatus();
void blinkLED(int blinkRate, int numBlinks);
void wifiStatusLED();

// RFID
String getRandomRFID();
void triggerRFID(int pinNumber);
String makeRFIDPostRequest(String rfid);
void sendRFIDPostRequest(String rfid);

// System
bool checkSystemStatus();
bool activateSystem();

// Function declarations
bool requestSessionId();
bool hasValidSession();
void resetProcessState();
void executeStateMachine();

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

/*

  RFID FUNCTIONS

*/

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
  // Create a JSON payload with the RFID tag and session ID
  String jsonBody = "{\"rfid_tag\":\"" + rfid + "\"";

  // Add session_id if we have one
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

  // Check if system is active and we have a session ID
  if (!systemActive)
  {
    Serial.println("System not active, cannot send RFID.");
    return;
  }

  if (currentSessionId.length() == 0)
  {
    Serial.println("No session ID, cannot send RFID.");
    return;
  }

  // Make a POST request to the server
  String rfidPostData = makeRFIDPostRequest(rfid);

  Serial.println("Connecting to server: " + String(server) + ":" + String(port));

  // Begin the request
  client.beginRequest();
  client.post("/api/rfid");
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", rfidPostData.length());
  client.beginBody();
  client.print(rfidPostData);
  client.endRequest();

  // Read the response
  int statusCode = client.responseStatusCode();
  String response = client.responseBody();
  Serial.print("Response Status Code: ");
  Serial.println(statusCode);
  Serial.print("Response Body: ");
  Serial.println(response);

  // Check response for different status codes
  if (statusCode == 400 && response.indexOf("System not activated") > -1)
  {
    // System is not active
    systemActive = false;
    sessionValid = false;
    Serial.println("System is not active. Session invalidated.");
  }
  else if (statusCode == 202 || statusCode == 200)
  {
    // Successful response
    Serial.println("RFID request successful!");
    blinkLED(50, 1);
  }
  else
  {
    Serial.println("RFID request failed!");
    if (response.indexOf("Session not found") > -1)
    {
      sessionValid = false;
      currentSessionId = "";
      Serial.println("Session invalid or expired.");
    }
    blinkLED(WIFI_ERROR_BLINK, 3);
  }
}

// Function to request a session ID from the server
bool requestSessionId()
{
  Serial.println("\nRequesting session ID from server...");

  // Reset client state before making a new request
  client.stop();
  delay(50); // Small delay to ensure clean connection state

  WiFiClient freshClient;
  HttpClient sessionClient(freshClient, server, port);

  // Begin the request with the fresh client
  sessionClient.beginRequest();
  sessionClient.get("/api/session");
  sessionClient.endRequest();

  // Read the response status code
  int statusCode = sessionClient.responseStatusCode();
  Serial.print("Session request status code: ");
  Serial.println(statusCode);

  // Read the response body
  String response = sessionClient.responseBody();
  Serial.print("Session response: ");
  Serial.println(response);

  // Debug the full response
  Serial.println("Response length: " + String(response.length()));
  for (int i = 0; i < response.length(); i++)
  {
    Serial.print(response[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  // Check if the request was successful
  if (statusCode == 200 || (statusCode < 0 && response.length() > 0))
  {
    // Extract session_id from response json using more robust parsing
    if (response.indexOf("session_id") > -1)
    {
      int sessionIdIndex = response.indexOf("\"session_id\":\"");
      if (sessionIdIndex > 0)
      {
        sessionIdIndex += 13; // Length of "session_id":"
        int sessionIdEndIndex = response.indexOf("\"", sessionIdIndex);
        if (sessionIdEndIndex > sessionIdIndex)
        {
          currentSessionId = response.substring(sessionIdIndex, sessionIdEndIndex);
          Serial.print("Received session ID: ");
          Serial.println(currentSessionId);
          sessionValid = true;
          blinkLED(100, 2); // Visual feedback for successful session acquisition
          return true;
        }
      }

      // Try alternate format (just in case)
      sessionIdIndex = response.indexOf("\"session_id\":");
      if (sessionIdIndex > 0)
      {
        sessionIdIndex += 12; // Length of "session_id":
        // Skip whitespace
        while (sessionIdIndex < response.length() &&
               (response.charAt(sessionIdIndex) == ' ' ||
                response.charAt(sessionIdIndex) == '"'))
        {
          sessionIdIndex++;
        }
        int sessionIdEndIndex = response.indexOf("\"", sessionIdIndex);
        if (sessionIdEndIndex < 0)
        {
          sessionIdEndIndex = response.indexOf(",", sessionIdIndex);
        }
        if (sessionIdEndIndex < 0)
        {
          sessionIdEndIndex = response.indexOf("}", sessionIdIndex);
        }
        if (sessionIdEndIndex > sessionIdIndex)
        {
          currentSessionId = response.substring(sessionIdIndex, sessionIdEndIndex);
          Serial.print("Received session ID (alt format): ");
          Serial.println(currentSessionId);
          sessionValid = true;
          blinkLED(100, 2);
          return true;
        }
      }
    }
  }

  // If we reach here, we failed to get a session ID
  Serial.println("Failed to obtain session ID");
  sessionValid = false;
  return false;
}

// Check if we have a valid session
bool hasValidSession()
{
  return currentSessionId.length() > 0 && sessionValid;
}

// Reset the process state machine
void resetProcessState()
{
  currentState = IDLE;
  stateStartTime = millis();
}

// Execute one step of the state machine
void executeStateMachine()
{
  unsigned long currentTime = millis();
  unsigned long stateElapsedTime = currentTime - stateStartTime;

  // Check for state timeout
  if (stateElapsedTime > STATE_TIMEOUT && currentState != IDLE && currentState != COOLDOWN)
  {
    Serial.println("State timeout! Resetting to IDLE state.");
    resetProcessState();
    return;
  }

  // State machine logic
  switch (currentState)
  // print the current state
  {
  case IDLE:
    // Move to checking system state
    Serial.println("Starting RFID process...");
    currentState = CHECKING_SYSTEM;
    stateStartTime = millis();
    break;

  case CHECKING_SYSTEM:
    // Check if system is active
    if (checkSystemStatus())
    {
      if (!systemActive)
      {
        Serial.println("System not active, activating...");
        if (activateSystem())
        {
          Serial.println("System activated, requesting session...");
          currentState = REQUESTING_SESSION;
          stateStartTime = millis();
        }
        else
        {
          Serial.println("Failed to activate system, returning to IDLE...");
          currentState = COOLDOWN;
          stateStartTime = millis();
        }
      }
      else
      {
        Serial.println("System already active, requesting session...");
        currentState = REQUESTING_SESSION;
        stateStartTime = millis();
      }
    }
    else
    {
      Serial.println("System check failed, returning to IDLE...");
      currentState = COOLDOWN;
      stateStartTime = millis();
    }
    break;

  case REQUESTING_SESSION:
    // Request a session ID
    if (requestSessionId())
    {
      Serial.println("Session ID received, ready to send RFID...");
      currentState = SESSION_READY;
      stateStartTime = millis();
    }
    else
    {
      Serial.println("Failed to get session ID, checking system status...");
      currentState = CHECKING_SYSTEM;
      stateStartTime = millis();
    }
    break;

  case SESSION_READY:
    // We have a valid session, send RFID
    if (hasValidSession())
    {
      Serial.println("Valid session found, sending RFID data...");
      String rfid = getRandomRFID();
      currentState = SENDING_RFID;
      stateStartTime = millis();
      sendRFIDPostRequest(rfid); // This sends the actual RFID data
    }
    else
    {
      Serial.println("Session became invalid, requesting new session...");
      currentState = REQUESTING_SESSION;
      stateStartTime = millis();
    }
    break;

  case SENDING_RFID:
    // RFID data has been sent, go to cooldown
    Serial.println("RFID process complete, entering cooldown...");
    currentState = COOLDOWN;
    stateStartTime = millis();
    break;

  case COOLDOWN:
    // Wait before starting a new cycle
    if (stateElapsedTime >= COOLDOWN_PERIOD)
    {
      Serial.println("Cooldown complete, returning to IDLE state...");
      currentState = IDLE;
      stateStartTime = millis();
    }
    break;
  }
}

/*

  SYSTEM FUNCTIONS

*/

// Function to check if the system is active
bool checkSystemStatus()
{
  Serial.println("\nChecking system status...");

  // Begin the request
  client.beginRequest();

  // Set the endpoint - using /test endpoint to check if server is reachable
  client.get("/api/test");

  // Complete the request
  client.endRequest();

  // Read the response status code
  int statusCode = client.responseStatusCode();
  Serial.print("System check status code: ");
  Serial.println(statusCode);

  // Check if the request was successful
  if (statusCode == 200 || statusCode < 0) // hardcoding this for now because idk how to fix a negative arduino status code
  {
    Serial.println("Server is reachable!");
    return true;
  }
  else
  {
    Serial.println("Failed to reach server or system is inactive");
    blinkLED(WIFI_ERROR_BLINK, 2);
    return false;
  }
}

// Function to activate the system
bool activateSystem()
{
  int retries = 0;
  const int maxRetries = 3;
  while (retries < maxRetries)
  {
    Serial.println("\nActivating system...");
    client.beginRequest();
    client.get("/api/activate");
    client.endRequest();
    int statusCode = client.responseStatusCode();
    Serial.print("Activation status code: ");
    Serial.println(statusCode);
    Serial.print("Activation response: ");
    Serial.println(client.responseBody());
    if (statusCode == 200)
    {
      Serial.println("System activated successfully!");
      systemActive = true;
      systemActivationTime = millis();
      blinkLED(50, 3);
      return true;
    }
    else
    {
      Serial.println("Failed to activate system, retrying...");
      retries++;
      delay(2000); // Wait 2 seconds before retrying
    }
  }
  Serial.println("Failed to activate system after multiple attempts.");
  systemActive = false;
  blinkLED(WIFI_ERROR_BLINK, 3);
  return false;
}

// ----------------
// Main Setup and Loop
// ----------------

void setup()
{
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(RFID_PIN, INPUT); // TODO: does this need to be a pullup?

  // initialize serial communication
  Serial.begin(9600);

  // Print a welcome message
  Serial.println("\n\n=== Arduino Uno R4 WiFi RFID Client ===");
  Serial.println("Starting up...");

  // Wait for Serial to be ready (for debugging)
  // Timeout after 5 seconds to that we do not have to open the serial monitor
  unsigned long startTime = millis();
  while (!Serial && (millis() - startTime < 5000))
    ;

  // Fast blink 3 times to indicate boot sequence
  blinkLED(200, 3);

  // Properly initialize random number generator
  randomSeed(analogRead(0));

  // Connect to WiFi network with visual feedback
  connectToWifi();

  Serial.println("Setup complete! Starting in IDLE state...");
  resetProcessState();
}

void loop()
{
  Serial.println("\n\n=== Main Loop ===");
  // Check WiFi status periodically
  checkWifiStatus();

  // Visual indicator of current WiFi status every few seconds
  static unsigned long lastLedUpdate = 0;
  if (millis() - lastLedUpdate > 5000)
  {
    wifiStatusLED();
    lastLedUpdate = millis();
  }

  // execute the RFID process state machine
  executeStateMachine();
}