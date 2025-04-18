#include <Arduino.h>

// put function declarations here:
int myFunction(int, int);

void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.println("Hello, World!");
  delay(1000);
}
