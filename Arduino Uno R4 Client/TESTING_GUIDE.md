# Arduino Client Testing Guide

## 🔄 Pre-Test Checklist
- [ ] Mobile hotspot is turned ON
- [ ] Laptop is connected to mobile hotspot
- [ ] Arduino Uno R4 is connected to laptop via USB
- [ ] Python environment with Flask is set up

## 🖥️ Server Setup
1. Open terminal in your project directory
2. Activate your Python virtual environment (if using one)
3. Start the Flask server:
```bash
cd server
python app.py
```
4. Verify server is running by visiting `http://localhost:5000` in your browser

## 🔧 PlatformIO Workflow
1. **Build the Project**
   - Click the checkmark icon (✓) in the bottom toolbar
   - Wait for "SUCCESS" message in the terminal

2. **Upload to Arduino**
   - Click the right arrow icon (→) in the bottom toolbar
   - Wait for "SUCCESS" message in the terminal

3. **Open Serial Monitor**
   - Click the beaker icon (⚗️) in the bottom toolbar
   - Set baud rate to 9600
   - Monitor the output for system status

## 🚨 Troubleshooting
1. **WiFi Connection Issues**
   - Check mobile hotspot is ON
   - Verify correct SSID and password in code
   - Check Serial Monitor for specific error messages

2. **Server Connection Issues**
   - Verify Flask server is running
   - Check local IP address in Arduino code
   - Ensure both devices are on same network

3. **Upload Issues**
   - Check USB connection
   - Verify correct board selected in PlatformIO
   - Try resetting Arduino

## 📝 Notes
- Default local server IP: 172.20.10.2
- Default port: 5000
- Mock RFID mode can be toggled with `RFID_MOCK` constant
- LED patterns indicate different states:
  - Fast blink: Connecting
  - Slow blink: Connected
  - Error pattern: Connection issues 