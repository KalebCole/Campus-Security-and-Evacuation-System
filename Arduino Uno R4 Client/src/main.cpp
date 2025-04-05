#include <Arduino.h>
#include <WiFiS3.h>
#include <WiFiSSLClient.h>
#include <WiFiClient.h>

// Resource:
// 1. https://www.elithecomputerguy.com/2019/07/write-post-data-to-server-with-arduino-uno-with-wifi/

// Constants
const bool RFID_MOCK = true;       // Set to true to use mock RFID database
const int RFID_PIN = 2;            // RFID reader pins
const bool isNgrokEnabled = true;  // Keep ngrok enabled but for TCP

// System activity constants
bool systemActive = false;         // System activation status
const int ACTIVATION_DELAY = 2000; // Wait 2 seconds after activation before sending RFID

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

// Create both client types
WiFiSSLClient sslClient;
WiFiClient regularClient;

// Server connection details - conditional based on isNgrokEnabled
const char *ngrokServer = "dory-actual-hedgehog.ngrok-free.app";  // Your ngrok TCP URL
const int ngrokPort = 12345;  // Your ngrok TCP port (will be different from 5000)
const char *localServer = "172.20.10.2";
const int localPort = 5000;

// Define these based on isNgrokEnabled (will be set in setup())
const char *server;
int port;

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

// Add new constants for state machine
const int WIFI_TIMEOUT = 30000;    // 30 seconds to connect to WiFi
const int ERROR_COOLDOWN = 5000;   // 5 seconds in error state
const int STATE_TIMEOUT = 10000;   // 10 seconds timeout for any state

// Update ProcessState enum
enum ProcessState {
  CONNECTING_WIFI,    // Initial state for WiFi connection
  IDLE,               // System is idle after WiFi connection
  CHECKING_SYSTEM,    // Checking if system is active
  REQUESTING_SESSION, // Requesting a session ID
  SESSION_READY,      // Session is ready, waiting for RFID
  WAITING_FOR_RFID,   // Waiting for RFID trigger
  SENDING_RFID,       // Sending RFID data
  COOLDOWN,           // Cooldown period between RFID cycles
  ERROR_STATE         // Error state for handling failures
};

// Current state in the RFID process
ProcessState currentState = CONNECTING_WIFI;

// Timing variables
unsigned long stateStartTime = 0;
const int COOLDOWN_PERIOD = 5000; // 5 seconds between complete cycles

// Session management
bool sessionValid = false;
const int SESSION_RETRY_INTERVAL = 10000; // 10 seconds between session retries
unsigned long lastSessionRequestTime = 0;

// Add logging constants
const char* LOG_SEPARATOR = "==========================================";
const char* STATE_SEPARATOR = "------------------------------------------";
const char* ERROR_SEPARATOR = "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!";

// Add logging helper function
void logState(const char* message, bool isError = false) {
  Serial.println();
  if (isError) {
    Serial.println(ERROR_SEPARATOR);
    Serial.print("ERROR: ");
  } else {
    Serial.println(STATE_SEPARATOR);
  }
  Serial.print("Time: ");
  Serial.print(millis());
  Serial.print(" | State: ");
  Serial.print(currentState);
  Serial.print(" | ");
  Serial.println(message);
  if (isError) {
    Serial.println(ERROR_SEPARATOR);
  } else {
    Serial.println(STATE_SEPARATOR);
  }
  Serial.println();
}

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

// Session
bool requestSessionId();
bool hasValidSession();

// State Machine
void resetProcessState();
void executeStateMachine();

// Create TCP client
WiFiClient tcpClient;

// Update makeHttpRequest to use TCP
String makeTcpRequest(String method, String path, String requestBody = "") {
  Serial.print("Making TCP request to ");
  Serial.println(server);
  Serial.print("Port: ");
  Serial.println(port);

  bool connected = false;
  
  // Attempt TCP connection
  Serial.println("Attempting TCP connection...");
  connected = tcpClient.connect(server, port);
  
  if (connected) {
    Serial.println("TCP Connected to server");
    
    // Create a simple message format
    String message = method + " " + path + "\n";
    if (requestBody.length() > 0) {
      message += "Content-Type: application/json\n";
      message += "Content-Length: " + String(requestBody.length()) + "\n\n";
      message += requestBody;
    }
    message += "\n";
    
    // Send the message
    tcpClient.print(message);
    
    // Wait for response
    unsigned long timeout = millis();
    while (tcpClient.available() == 0) {
      if (millis() - timeout > 10000) {
        Serial.println("Request timeout!");
        tcpClient.stop();
        return "";
      }
    }
    
    // Read response
    String response = "";
    timeout = millis();
    while (tcpClient.available() && (millis() - timeout < 10000)) {
      char c = tcpClient.read();
      response += c;
    }
    
    // Close connection
    tcpClient.stop();
    return response;
  }
  
  Serial.println("TCP Connection failed");
  return "";
}

// Function to print detailed WiFi status information
void printWifiStatus()
{
  // Print basic WiFi information
  Serial.println("\n----- WiFi Status -----");

  // Connection status
  Serial.print("Status: ");
  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("CONNECTED");
  }
  else
  {
    Serial.println("NOT CONNECTED");
  }

  // Print network info if connected
  if (WiFi.status() == WL_CONNECTED)
  {
    // SSID name
    Serial.print("SSID: ");
    Serial.println(WiFi.SSID());

    // IP address
    IPAddress ip = WiFi.localIP();
    Serial.print("IP: ");
    Serial.println(ip);

    // Signal strength
    Serial.print("Signal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  }

  Serial.println("---------------------");
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

// Store the most recently read RFID value
String currentRFID = "";

// Function to handle RFID detection when we receive a pin on high
void triggerRFID(int pinNumber)
{
  if (RFID_MOCK)
  {
    // Just get the RFID value, don't send it yet
    currentRFID = getRandomRFID();
    Serial.print("Mock RFID detected: ");
    Serial.println(currentRFID);
    return;
  }

  // Check if the pin is high and store physical RFID
  if (digitalRead(pinNumber) == HIGH)
  {
    // In a real implementation, you'd read from actual RFID hardware
    // For now, using mock data for demonstration
    currentRFID = getRandomRFID();
    Serial.print("Physical RFID detected: ");
    Serial.println(currentRFID);
  }
}
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

// Update makeHttpRequest function
String makeHttpRequest(String method, String path, String requestBody = "") {
  Serial.print("Making ");
  Serial.print(method);
  Serial.print(" request to ");
  Serial.println(server);
  Serial.print("Path: ");
  Serial.println(path);
  Serial.print("Port: ");
  Serial.println(port);

  bool connected = false;

  if (isNgrokEnabled) {
    // Use SSL client for HTTPS (ngrok)
    Serial.println("Using HTTPS connection (SSL)");
    
    // Debug SSL setup
    debugSSLConnection();
    
    // Set certificate
    sslClient.setCACert(ngrok_root_cert);
    
    // Attempt connection
    connected = sslClient.connect(server, port);
    
    if (connected) {
      Serial.println("SSL Connected to server");
      
      // Create the HTTP request
      sslClient.print(method + " " + path + " HTTP/1.1\r\n");
      sslClient.print("Host: ");
      sslClient.print(server);
      sslClient.print("\r\n");

      if (requestBody.length() > 0)
      {
        sslClient.print("Content-Type: application/json\r\n");
        sslClient.print("Content-Length: ");
        sslClient.print(requestBody.length());
        sslClient.print("\r\n");
      }

      sslClient.print("Connection: close\r\n\r\n"); // End of headers

      // Send the body if needed
      if (requestBody.length() > 0)
      {
        sslClient.print(requestBody);
      }

      // Wait for response
      unsigned long timeout = millis();
      while (sslClient.available() == 0)
      {
        if (millis() - timeout > 10000)
        {
          Serial.println("Request timeout!");
          sslClient.stop();
          return "";
        }
      }

      // Skip HTTP headers
      char endOfHeaders[] = "\r\n\r\n";
      bool headerFound = false;
      int matchedChars = 0;

      timeout = millis();
      while (sslClient.available() && !headerFound && (millis() - timeout < 10000))
      {
        char c = sslClient.read();

        // Check if we're at the end of headers
        if (c == endOfHeaders[matchedChars])
        {
          matchedChars++;
          if (matchedChars == strlen(endOfHeaders))
          {
            headerFound = true;
          }
        }
        else
        {
          matchedChars = 0;
        }
      }

      // Now read the response body
      String response = "";
      timeout = millis();
      while (sslClient.available() && (millis() - timeout < 10000))
      {
        char c = sslClient.read();
        response += c;
      }

      // Close the connection
      sslClient.stop();
      return response;
    }
  }
  else
  {
    // Use regular client for HTTP (local server)
    Serial.println("Using HTTP connection (no SSL)");
    connected = regularClient.connect(server, port);

    if (connected)
    {
      Serial.println("Connected to server");

      // Create the HTTP request
      regularClient.print(method + " " + path + " HTTP/1.1\r\n");
      regularClient.print("Host: ");
      regularClient.print(server);
      regularClient.print("\r\n");

      if (requestBody.length() > 0)
      {
        regularClient.print("Content-Type: application/json\r\n");
        regularClient.print("Content-Length: ");
        regularClient.print(requestBody.length());
        regularClient.print("\r\n");
      }

      regularClient.print("Connection: close\r\n\r\n"); // End of headers

      // Send the body if needed
      if (requestBody.length() > 0)
      {
        regularClient.print(requestBody);
      }

      // Wait for response
      unsigned long timeout = millis();
      while (regularClient.available() == 0)
      {
        if (millis() - timeout > 10000)
        {
          Serial.println("Request timeout!");
          regularClient.stop();
          return "";
        }
      }

      // Skip HTTP headers
      char endOfHeaders[] = "\r\n\r\n";
      bool headerFound = false;
      int matchedChars = 0;

      timeout = millis();
      while (regularClient.available() && !headerFound && (millis() - timeout < 10000))
      {
        char c = regularClient.read();

        // Check if we're at the end of headers
        if (c == endOfHeaders[matchedChars])
        {
          matchedChars++;
          if (matchedChars == strlen(endOfHeaders))
          {
            headerFound = true;
          }
        }
        else
        {
          matchedChars = 0;
        }
      }

      // Now read the response body
      String response = "";
      timeout = millis();
      while (regularClient.available() && (millis() - timeout < 10000))
      {
        char c = regularClient.read();
        response += c;
      }

      // Close the connection
      regularClient.stop();
      return response;
    }
  }

  Serial.println("Connection failed");
  return "";
}

// Function to extract status code from HTTP response
int getStatusCode(String response)
{
  if (response.indexOf("200 OK") > -1)
    return 200;
  if (response.indexOf("201 Created") > -1)
    return 201;
  if (response.indexOf("202 Accepted") > -1)
    return 202;
  if (response.indexOf("400 Bad Request") > -1)
    return 400;
  if (response.indexOf("404 Not Found") > -1)
    return 404;
  if (response.indexOf("500 Internal") > -1)
    return 500;
  return -1; // Unknown status code
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

  // Create JSON payload
  String rfidPostData = makeRFIDPostRequest(rfid);

  // Make the POST request
  String response = makeHttpRequest("POST", "/api/rfid", rfidPostData);

  // Try to determine status code from response
  int statusCode = getStatusCode(response);
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
  else if (statusCode == 202 || statusCode == 200 || statusCode < 0) // hardcoding this bc idk why the arduino return -1
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

  String response = makeHttpRequest("GET", "/api/session");

  Serial.print("Session response: ");
  Serial.println(response);

  // Debug the full response
  Serial.println("Response length: " + String(response.length()));

  // Check if the response contains session_id
  if (response.indexOf("session_id") > -1)
  {
    int sessionIdIndex = response.indexOf("\"session_id\":\"");
    if (sessionIdIndex > 0)
    {
      sessionIdIndex += 13; // Length of "session_id":""
      int sessionIdEndIndex = response.indexOf("\"", sessionIdIndex);
      if (sessionIdEndIndex > sessionIdIndex)
      {
        currentSessionId = response.substring(sessionIdIndex, sessionIdEndIndex);
        Serial.print("Received session ID: ");
        Serial.println(currentSessionId);
        sessionValid = true;
        blinkLED(100, 2); // Visual feedback
        return true;
      }
    }

    // Try alternate format
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

  // State timeout check
  if (stateElapsedTime > STATE_TIMEOUT && 
      currentState != IDLE && 
      currentState != COOLDOWN &&
      currentState != ERROR_STATE) {
    logState("State timeout! Moving to ERROR_STATE", true);
    currentState = ERROR_STATE;
    stateStartTime = millis();
    return;
  }

  switch (currentState) {
    case CONNECTING_WIFI:
      if (WiFi.status() == WL_CONNECTED) {
        logState("WiFi connected, moving to IDLE");
        currentState = IDLE;
        stateStartTime = millis();
      } else if (stateElapsedTime > WIFI_TIMEOUT) {
        logState("WiFi connection timeout", true);
        currentState = ERROR_STATE;
        stateStartTime = millis();
      } else {
        connectToWifi();
      }
      break;

    case ERROR_STATE:
      // Blink error pattern
      blinkLED(WIFI_ERROR_BLINK, 3);
      
      // Try to recover after ERROR_COOLDOWN
      if (stateElapsedTime > ERROR_COOLDOWN) {
        logState("Attempting to recover from error state");
        currentState = CONNECTING_WIFI;
        stateStartTime = millis();
      }
      break;

    case IDLE:
      logState("Starting RFID process");
      currentState = WAITING_FOR_RFID;
      stateStartTime = millis();
      break;

    case WAITING_FOR_RFID:
      if (currentRFID.length() > 0) {
        logState("RFID detected, checking system");
        currentState = CHECKING_SYSTEM;
        stateStartTime = millis();
      }
      break;

    case CHECKING_SYSTEM:
      if (checkSystemStatus()) {
        if (!systemActive) {
          logState("System not active, attempting activation");
          if (activateSystem()) {
            logState("System activated, requesting session");
            currentState = REQUESTING_SESSION;
            stateStartTime = millis();
          } else {
            logState("Failed to activate system", true);
            currentState = ERROR_STATE;
            stateStartTime = millis();
          }
        } else {
          logState("System already active, requesting session");
          currentState = REQUESTING_SESSION;
          stateStartTime = millis();
        }
      } else {
        logState("System check failed", true);
        currentState = ERROR_STATE;
        stateStartTime = millis();
      }
      break;

    case REQUESTING_SESSION:
      if (requestSessionId()) {
        logState("Session ID received, ready to send RFID");
        currentState = SESSION_READY;
        stateStartTime = millis();
      } else {
        logState("Failed to get session ID", true);
        currentState = ERROR_STATE;
        stateStartTime = millis();
      }
      break;

    case SESSION_READY:
      if (hasValidSession()) {
        logState("Valid session found, sending RFID data");
        currentState = SENDING_RFID;
        stateStartTime = millis();
        sendRFIDPostRequest(currentRFID);
      } else {
        logState("Session became invalid", true);
        currentState = ERROR_STATE;
        stateStartTime = millis();
      }
      break;

    case SENDING_RFID:
      logState("RFID process complete, entering cooldown");
      currentState = COOLDOWN;
      stateStartTime = millis();
      break;

    case COOLDOWN:
      if (stateElapsedTime >= COOLDOWN_PERIOD) {
        logState("Cooldown complete, returning to IDLE state");
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

  int retries = 0;
  const int maxRetries = 3;

  while (retries < maxRetries)
  {
    // Make HTTP request to test endpoint
    String response = makeHttpRequest("GET", "/api/test");

    // Extract status code
    int statusCode = getStatusCode(response);
    Serial.print("System check status code: ");
    Serial.println(statusCode);

    // Check if the server is reachable
    if (statusCode == 200 || (statusCode < 0 && response.length() > 0))
    {
      Serial.println("Server is reachable!");

      // IMPORTANT: Just because server is reachable doesn't mean system is activated
      // Need to check if system is activated by looking at the session response
      String sessionResponse = makeHttpRequest("GET", "/api/session");

      if (sessionResponse.indexOf("System not activated") > -1 ||
          sessionResponse.indexOf("\"error\"") > -1)
      {
        Serial.println("System is reachable but NOT activated");
        systemActive = false; // Make sure to set this to false
        return true;          // Return true so we can activate it in the state machine
      }
      else if (sessionResponse.indexOf("\"success\"") > -1 || sessionResponse.indexOf("session_id") > -1)
      {
        Serial.println("System is both reachable AND activated");
        systemActive = true;
        return true;
      }
      else
      {
        Serial.println("Unexpected session response, assuming system needs activation");
        systemActive = false;
        return true;
      }
    }
    else
    {
      // If failed, increment retry counter and try again
      Serial.println("Failed to reach server, retrying...");
      retries++;

      if (retries < maxRetries)
      {
        // Visual feedback for retry
        blinkLED(WIFI_ERROR_BLINK, 1);
        delay(1000); // Wait 1 second before retrying
      }
    }
  }

  // If we've exhausted all retries, report failure
  Serial.println("Failed to reach server after multiple attempts");
  blinkLED(WIFI_ERROR_BLINK, 2);
  systemActive = false;
  return false;
}

// Function to activate the system
bool activateSystem()
{
  int retries = 0;
  const int maxRetries = 3;
  while (retries < maxRetries)
  {
    Serial.println("\nActivating system...");

    // Make HTTP request to activate endpoint
    String response = makeHttpRequest("GET", "/api/activate");

    int statusCode = getStatusCode(response);
    Serial.print("Activation status code: ");
    Serial.println(statusCode);
    Serial.print("Activation response: ");
    Serial.println(response);

    if ((statusCode == 200 || statusCode < 0) &&
        (response.indexOf("\"success\"") > -1 || response.indexOf("activated") > -1))
    {
      Serial.println("System activated successfully!");
      systemActive = true;
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
  // Set server and port based on isNgrokEnabled
  if (isNgrokEnabled)
  {
    server = ngrokServer;
    port = ngrokPort;
    Serial.println("Using Ngrok configuration");
  }
  else
  {
    server = localServer;
    port = localPort;
    Serial.println("Using local server configuration");
  }

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(RFID_PIN, INPUT);

  // initialize serial communication
  Serial.begin(9600);

  // Print a welcome message
  Serial.println(LOG_SEPARATOR);
  Serial.println("=== Arduino Uno R4 WiFi RFID Client ===");
  Serial.println("Starting up...");
  Serial.println(LOG_SEPARATOR);

  // Wait for Serial to be ready (for debugging)
  unsigned long startTime = millis();
  while (!Serial && (millis() - startTime < 5000))
    ;

  // Fast blink 3 times to indicate boot sequence
  blinkLED(200, 3);

  // Properly initialize random number generator
  randomSeed(analogRead(0));

  // Start in CONNECTING_WIFI state
  currentState = CONNECTING_WIFI;
  stateStartTime = millis();
  logState("Initializing in CONNECTING_WIFI state");
}

void loop()
{
  // Check WiFi status
  if (WiFi.status() != WL_CONNECTED && 
      currentState != CONNECTING_WIFI && 
      currentState != ERROR_STATE) {
    logState("WiFi connection lost!", true);
    currentState = CONNECTING_WIFI;
    stateStartTime = millis();
    return;
  }

  // Visual indicator of current WiFi status every few seconds
  static unsigned long lastLedUpdate = 0;
  if (millis() - lastLedUpdate > 5000) {
    wifiStatusLED();
    lastLedUpdate = millis();
  }

  // Check for RFID input if in the right state and not in mock mode
  if (currentState == WAITING_FOR_RFID) {
    if (RFID_MOCK) {
      // In mock mode, generate RFID immediately
      triggerRFID(RFID_PIN);
    } else {
      // Real hardware mode
      static unsigned long lastRFIDCheck = 0;
      if (millis() - lastRFIDCheck >= 200) { // Debounce
        lastRFIDCheck = millis();
        if (digitalRead(RFID_PIN) == HIGH) {
          triggerRFID(RFID_PIN);
        }
      }
    }
  }

  // Execute the state machine
  executeStateMachine();

  // Reset RFID data after sending
  if (currentState == COOLDOWN) {
    currentRFID = "";
  }

  // Small delay to prevent CPU overload
  delay(50);
}