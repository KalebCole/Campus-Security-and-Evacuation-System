# Arduino Client Testing Guide

## 🧪 Test Scenarios

### 1. RFID Testing
- [ ] Verify RFID pin detection (HIGH = detected)
- [ ] Test debounce timing (1000ms)
- [ ] Check mock RFID value generation
- [ ] Verify MQTT message format:
  ```json
  {
    "device_id": "arduino_uno_r4",
    "rfid": "MOCK_VALUE",
    "timestamp": 1234567890
  }
  ```
- [ ] Test state transition: ACTIVE_WAITING → ACTIVE_SESSION

### 2. Motion Testing
- [ ] Verify motion pin detection (HIGH = motion)
- [ ] Test debounce timing (1000ms)
- [ ] Check state transitions:
  - [ ] IDLE → ACTIVE_WAITING (on motion)
  - [ ] ACTIVE_WAITING → IDLE (no motion)
- [ ] Verify session timeout (3 seconds)

### 3. Emergency Testing
- [ ] Verify emergency pin detection (HIGH = emergency)
- [ ] Test immediate state override from any state
- [ ] Check MQTT emergency message:
  ```json
  {
    "device_id": "arduino_uno_r4",
    "event": "emergency",
    "action": "unlock_triggered",
    "timestamp": 1234567890
  }
  ```
- [ ] Verify unlock signal (500ms pulse)
- [ ] Test emergency timeout (10 seconds)
- [ ] Check return to IDLE after timeout

## 🔧 Test Setup
1. Create test directories:
   ```
   test/
   ├── test_rfid/
   ├── test_motion/
   └── test_emergency/
   ```

2. Required mocks:
   - [ ] Time control (mockMillis)
   - [ ] Pin states (RFID, motion, emergency)
   - [ ] MQTT client
   - [ ] State machine tracking

## 🚀 Running Tests
1. Build and run all tests:
   ```powershell
   platformio test
   ```

2. Run specific test suite:
   ```powershell
   platformio test -e uno_r4_wifi -f test_rfid
   platformio test -e uno_r4_wifi -f test_motion
   platformio test -e uno_r4_wifi -f test_emergency
   ```

## 📝 Notes
- Tests should be independent
- Use mock time for testing timeouts
- Verify MQTT messages match expected format
- Check state transitions are correct
- Emergency should override all other states 