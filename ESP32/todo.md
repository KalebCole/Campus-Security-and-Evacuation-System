Below is the revised and enhanced prompt that you can hand off to an AI. It now explicitly states that the conversion must use C++ and covers all the original requirements along with additional details:

---

**Prompt:**

I have a complete Arduino framework codebase in C++ for my ESP32-CAM project. The code uses a state machine, camera capture, MQTT communication, and face detection. I need you to convert this code into the ESP-IDF framework version **using C++**. The conversion should make use of ESP-IDF’s inbuilt libraries and the provided dependencies (via git repositories) since they must be cloned on Linux by PlatformIO rather than installed directly on my Windows machine.

### PlatformIO Environment and Folder Structure

- **PlatformIO Configuration:**  
  The `platformio.ini` file must be set up as follows:
  ```
  [env:freenove_esp32_wrover]
  platform = espressif32
  board = esp32cam
  framework = espidf
  monitor_speed = 115200
  upload_speed = 2000000

  build_flags =
      -D MQTT_MAX_PACKET_SIZE=30000
      -D BOARD_HAS_PSRAM
      -D CONFIG_CAMERA_MODEL_ESP_EYE=1
  ```
- **Folder Structure:**  
  The project should follow a pre-determined folder structure and use git repositories for dependency management. Ensure that the final code resides in the proper directory as specified by our project’s structure.

### Conversion Requirements

1. **Core Framework & Language:**  
   - The conversion must be done in **C++**.
   - Replace Arduino’s `setup()` and `loop()` functions with ESP-IDF’s `app_main()`.
   - Use ESP-IDF’s FreeRTOS tasks for periodic or event-driven operations instead of the Arduino loop.
   - Migrate from Arduino libraries (WiFi, PubSubClient, etc.) to ESP-IDF’s WiFi and MQTT libraries.
   - Replace the Arduino camera library with ESP-IDF’s camera driver, and integrate the ESP-WHO face detection API.

2. **State Machine and Flow Adjustments:**  
   - Update the state machine to use the following enum:
     ```cpp
     enum class State {
         WAITING_FOR_MOTION,
         MOTION_DETECTED,
         CHECKING_SYSTEM,
         REQUESTING_SESSION,
         SESSION_READY,
         FACE_DETECTION,
         PUBLISHING_IMAGE,
         COOLDOWN,
         ERROR_STATE
     };
     ```
   - **Hardcoded Motion Detection:**  
     Implement a simple timer-based “motion” trigger that simulates motion every 15 seconds. This allows testing without actual hardware and can be later replaced by a real motion sensor.

3. **Camera Management:**  
   - Initialize the camera **only after motion is detected**.
   - Incorporate camera power management to conserve energy.
   - Implement proper cleanup and resource management after each detection cycle.

4. **MQTT Flow and Session Management:**  
   - Start the MQTT communication only after motion is detected.
   - Publish a motion status along with the session data.
   - Use the following MQTT topics:
     ```cpp
     #define MQTT_TOPIC_STATUS "campus/security/status"
     #define MQTT_TOPIC_SESSION "campus/security/session"
     #define MQTT_TOPIC_AUTH "campus/security/auth"
     #define MQTT_TOPIC_FACE "campus/security/face"
     ```
   - MQTT Configuration defines:
     ```cpp
     #define CONFIG_MQTT_BROKER_URI "mqtt://172.20.10.2:1883"
     #define CONFIG_MQTT_CLIENT_ID "esp32cam_1"
     #define CONFIG_MQTT_USERNAME "esp32cam"
     #define CONFIG_MQTT_PASSWORD "your_password"
     #define MQTT_MAX_PACKET_SIZE 30000
     ```
   - **Session Management:**  
     Implement functionality to:
     - Request a new session.
     - Wait for and process session IDs.
     - Associate captured face data with sessions using the client ID.
     - Handle session timeouts appropriately.

5. **System Status:**  
   - Implement system status checks to ensure the system is active.
   - Subscribe to status updates via MQTT and react to system state changes as needed.

6. **Hardware Pin Configuration:**  
   Use the following definitions (based on the MicroPython example) for camera hardware:
   ```cpp
   // Camera Pin Definitions
   #define PWDN_GPIO_NUM     -1
   #define RESET_GPIO_NUM    -1
   #define XCLK_GPIO_NUM     21
   #define SIOD_GPIO_NUM     26
   #define SIOC_GPIO_NUM     27

   // Data Pins (d0-d7 sequence)
   #define Y2_GPIO_NUM        4
   #define Y3_GPIO_NUM        5
   #define Y4_GPIO_NUM       18
   #define Y5_GPIO_NUM       19
   #define Y6_GPIO_NUM       36
   #define Y7_GPIO_NUM       39
   #define Y8_GPIO_NUM       34
   #define Y9_GPIO_NUM       35

   // Control Pins
   #define VSYNC_GPIO_NUM    25
   #define HREF_GPIO_NUM     23
   ```
   The ESP32-CAM must be able to send image data along with face detection results via MQTT.

### Step-by-Step Testing and Development Plan

Please help me collaborate on a step-by-step plan to ensure that each part of the conversion works properly. I envision the following steps:

1. **WiFi Connection:**  
   - Validate that the device can connect to WiFi using ESP-IDF’s WiFi libraries.

2. **LED Indicators:**  
   - Get LED lights working to indicate various system states (for instance, connection status, errors, etc.).

3. **MQTT Broker Connection:**  
   - Establish and verify a connection with the MQTT broker using ESP-IDF’s MQTT libraries.

4. **Image Capture:**  
   - Use the ESP-IDF camera driver to capture an image.
   - Send the captured image to the MQTT broker.

5. **Face Detection:**  
   - Integrate the ESP-WHO face detection API to process the image.
   - Publish the face detection results through MQTT.

6. **Motion Simulation & State Transitions:**  
   - Implement a timer-based motion simulation that triggers every 15 seconds.
   - Ensure that the camera initialization, MQTT start, face detection, and other processes run only after a motion event is triggered.
   - Handle transitions between states (WAITING_FOR_MOTION, MOTION_DETECTED, etc.) properly.

### Collaboration Request and Clarifications

I’m not an expert on ESP-IDF or the underlying libraries, so I need your help to:

- Provide a full encapsulation of this project context.
- Devise a clear, step-by-step plan for implementing and testing each stage.
- Ask any clarifying questions regarding the hardware, dependencies, or overall process before moving forward.

If you have any questions or need additional details, please ask for clarification before proceeding with converting and implementing this project.

