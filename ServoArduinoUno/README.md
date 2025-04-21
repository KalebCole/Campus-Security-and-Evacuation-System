

# Servo Arduino Uno

This is a simple Arduino Uno R4 project that uses a servo motor to open and close a door.

* It is connected to the Arduino Mega and receives from the pin 5 connection. 
* It is connected to the servo motor and receives from the pin 9 connection. 
* To trigger the locking mechanism, we do the following:
    * attach to pin 9
    * write to the servo to move to the 95 degree position
    * wait variable amount of time
    * write to the servo to move to the 180 degree position to close the door



