# 📜 Arduino UNO R4 — Final Roles and Responsibilities

## 🔵 1. Monitor Emergency Input
- Continuously monitor a **dedicated emergency input pin** (e.g., fire alarm signal).
- **When emergency is triggered:**
  - **Immediately unlock** (send a wired signal to a second Arduino controlling the servo motor).
  - **Publish an emergency message** to MQTT (`campus/security/emergency`).

---

## 🔵 2. Monitor RFID Sensor Input
- Continuously monitor the **RFID input pin** (`RFID_PIN = 2`).
- **When RFID is detected (HIGH signal):**
  - **Generate a fake RFID value** (hardcoded or random for the demo).
  - **Send the fake RFID value to the ESP32CAM** (likely via a simple serial connection or pin-to-pin).

---

## 🔵 3. Subscribe to Unlock Commands (Normal Unlocking)
- **Subscribe to the MQTT topic** `campus/security/unlock`.
- **When an unlock command is received (from the API):**
  - Parse the JSON payload.
  - If it contains a valid unlock request (e.g., `{"action": "unlock"}`):
    - **Send a wired unlock signal** to the second Arduino controlling the servo motor.

**Example unlock payload from API:**
```json
{
  "action": "unlock",
  "session_id": "session_abc123",
  "timestamp": "2025-04-11T10:00:00Z"
}
```

---

## 🔵 4. Publish Emergency Events
- After an emergency unlock, **publish a message** to MQTT `campus/security/emergency`.
- Payload includes:
  - Event type (`emergency`)
  - Action taken (`unlock_signal_sent`)
  - Timestamp
  - Device ID

---

## 🔵 5. Suspend Normal Operations During Emergency
- When **emergency mode** is active:
  - **RFID detection stops**.
  - **Unlock commands from the API are ignored** unless designed otherwise (optional safety).
  - Only emergency unlocking and MQTT publishing are active.

---

# 📈 Arduino Input/Output Summary

| Input Signal / Message         | Action Taken                                              | Output |
|---------------------------------|-----------------------------------------------------------|--------|
| Emergency Pin goes LOW          | Immediate local unlock (send signal to servo Arduino) and MQTT publish | Unlock + MQTT |
| RFID Pin goes HIGH              | Generate fake RFID and send to ESP32CAM                   | Send fake RFID |
| MQTT Unlock Message Received    | Unlock (send signal to servo Arduino) after API verification | Unlock |

---

# 🛠 Connection Summary

- **Wi-Fi:**  
  Connects to Kaleb’s mobile hotspot (`SSID: "iPod Mini"`, `Password: "H0t$p0t!"`).

- **MQTT Broker:**  
  Connects to:
  - Broker IP: `172.20.10.2`
  - Port: `1883`
  - MQTT Client ID: `"arduino_uno_r4"`

- **MQTT Topics Used:**
  | Topic                         | Role                     |
  |-------------------------------|--------------------------|
  | `campus/security/emergency`    | Publish emergency events |
  | `campus/security/unlock`       | Subscribe to unlock commands |

---

# 🔥 Final Responsibilities Checklist

✅ Monitor emergency input pin.  
✅ Immediate unlock signal to second Arduino on emergency.  
✅ Publish emergency MQTT message.  
✅ Monitor RFID input pin.  
✅ Generate/send fake RFID to ESP32CAM.  
✅ Subscribe to unlock commands from API via MQTT.  
✅ Unlock door when API sends unlock command.  
✅ Suspend normal operations during emergency.
