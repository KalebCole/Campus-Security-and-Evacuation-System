

## Things to Add

- [ ] Manual Activation:
  - [ ] Pulling the MS-7 Fire Alarm station closes its internal circuit, sending a HIGH (3.3V) signal to Pin 7 on the Arduino Uno R4 WiFi.
  - [ ] GPIO Input Detection:
    - [ ] The Arduino monitors Pin 7 via interrupt-driven code:

```cpp
void setup() {
  pinMode(7, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(7), emergencyStop, FALLING);
}
```

- [ ] Emergency Stop:
  - [ ] The emergencyStop() function is triggered when the circuit is closed:

```cpp
void emergencyStop() {
  digitalWrite(8, HIGH);  // Activate strobe light via relay
  servo.write(0);         // Unlock door
  client.publish("campus/security/emergency/main-door", "{\"emergency\":true}");
}

```



