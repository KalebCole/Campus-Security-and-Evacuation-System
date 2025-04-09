# Errors

## API (routes)


### 


## Arduino Uno

### 🔧 Problem: Uploading to the Arduino Uno R4 WiFi failed with the following error:

```
Error: Please specify `upload_port` for environment or use global `--upload-port` option.
[upload] could not open port 'COM3': FileNotFoundError(2, 'The system cannot find the file specified.')
```

#### 🕵️ Root Cause
The Arduino Uno R4 WiFi was not properly recognized by the system, even though it appeared as a generic USB Serial Device (COM3). This caused PlatformIO to fail during the upload process.

#### ✅ Solution
Reset the Arduino Uno R4 WiFi by pressing the reset button on the board.

This restored normal communication, and the board reappeared on the correct COM port, allowing PlatformIO to upload successfully