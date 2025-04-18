#include <Arduino.h>

// Define which serial port to use for communication with the Mega
// We'll use Serial2 hardware UART, but reassign pins
HardwareSerial &MegaSerial = Serial2;

// Define the RX and TX pins on the ESP32 for Mega communication
const int ESP32_TX_PIN = 18; // Connect this to Mega RX (Pin 17)
const int ESP32_RX_PIN = 19; // Connect this to Mega TX (Pin 16)

// Define the baud rate for communication with Mega
const long MEGA_BAUD_RATE = 9600; // Changed to 9600

// Define the baud rate for the ESP32's USB Serial Monitor
const long DEBUG_BAUD_RATE = 115200; // Keep debug monitor at 115200

void setup()
{
  // Start the USB Serial Monitor connection
  Serial.begin(DEBUG_BAUD_RATE);
  while (!Serial)
    ; // Wait for serial port to connect
  Serial.println("\n--- ESP32 Serial Receiver Test (Pins 12/13, 9600 Baud) ---");
  Serial.println("Listening for 'E' from Mega...");

  Serial.print("Listening on ESP32 Serial2 ");
  Serial.print("(RX=");
  Serial.print(ESP32_RX_PIN);
  Serial.print(", TX=");
  Serial.print(ESP32_TX_PIN);
  Serial.print(") at ");
  Serial.print(MEGA_BAUD_RATE);
  Serial.println(" baud.");
  // Start the serial connection to the Mega on specific pins
  MegaSerial.begin(MEGA_BAUD_RATE, SERIAL_8N1, ESP32_RX_PIN, ESP32_TX_PIN);
}

void loop()
{
  // Check if data is available from the Mega
  if (MegaSerial.available() > 0)
  {
    // Read the incoming byte
    char receivedChar = MegaSerial.read();

    // Print what was received to the debug monitor
    Serial.print("Received from Mega: ");
    Serial.write(receivedChar); // Use write to handle potential non-printable chars

    // Check if it's the character we expect
    if (receivedChar == 'E')
    {
      Serial.println(" <-- Emergency signal 'E' detected!");
    }
    else
    {
      Serial.println(" <-- (Unexpected character)");
    }
  }

  // No delay needed, loop runs continuously
}