# Campus Security and Evacuation System - Deployment & Architecture

This document outlines the simplified deployment architecture, local development setup, and production strategy for the Campus Security and Evacuation System (CSES). Notifications are integrated into the **API service** to reduce complexity.

---

## **System Architecture**

### **Modular Service Breakdown**

| Service Name            | Description                                    | Technology         | Container Name         |
|-------------------------|------------------------------------------------|--------------------|------------------------|
| `api`                   | Core API service for authentication workflows and notification handling and mqtt handling for api | Flask              | `api`                  |
| `face_recognition`      | Face recognition service using GhostFaceNet   | Python             | `face_recognition`     |
| `database`              | PostgreSQL with pgVector for embeddings       | PostgreSQL         | `postgres`             |
| `mqtt-broker`           | Message broker for device communication       | Eclipse Mosquitto  | `mosquitto`            |
| `frontend-service`      | Security monitoring dashboard                 | React              | `frontend-service`     |

---

## **MQTT Architecture**

### **Topics and Message Flow**

| Topic                    | Publisher           | Subscriber         | Purpose                              |
|--------------------------|---------------------|--------------------|--------------------------------------|
| `campus/security/face`   | ESP32-CAM          | API Service        | Face detection data                  |
| `campus/security/rfid`   | Arduino Uno R4     | API Service        | RFID authentication data             |
| `campus/security/session`| API Service        | All Devices        | Session management and status        |
| `campus/security/activate`| Arduino Uno R4    | API Service, ESP32 | System activation                    |
| `campus/security/emergency/+`| All Devices   | All Components     | Emergency notifications              |

### **MQTT Message Formats**

1. **Face Detection**
```json
{
    "device_id": "esp32-cam-01",
    "image": "base64_encoded_image",
    "timestamp": "2024-04-09T12:00:00Z"
}
```

2. **RFID Authentication**
```json
{
    "rfid_tag": "A1B2C3D4",
    "device_id": "arduino-door-01",
    "timestamp": "2024-04-09T12:00:00Z"
}
```

3. **Session Management**
```json
{
    "session_id": "ABC123",
    "device_id": "arduino-door-01",
    "auth_status": "partial",
    "rfid_verified": false,
    "face_verified": false,
    "timestamp": "2024-04-09T12:00:00Z"
}
```

---

## **Architecture Diagram**

```
                           ┌─────────────────┐
                           │  Security Admin │
                           │    Interface    │
                           └────────┬────────┘
                                    │
                                    ▼
┌─────────────────┐     MQTT     ┌─────────────────┐     pgvector    ┌─────────────────┐
│   Arduino Uno   │◄──────────►│    MQTT Broker   │                │   PostgreSQL DB  │
│   RFID Client   │             └────────┬────────┘◄──────────────►│   (pgVector)    │
└─────────────────┘                      │                         └─────────────────┘
                                         │                                  ▲
┌─────────────────┐     MQTT             │                                  │
│    ESP32-CAM    │◄───────────┐         │                                  │
│  (ESP-WHO det.) │            ▼         ▼                                  │
└─────────────────┘     ┌─────────────────┐                                 │
                        │      API        │                                 │
                        │ (Notifications) │◄────────────────────────────────┘
                        └────────┬────────┘
                                 ▼
                        ┌─────────────────┐
                        │  Frontend UI    │
                        └─────────────────┘
```

---

## **Container Organization**

The system uses Docker containers for all backend services, organized in a hierarchical structure:

```
campus-security-system/
├── docker-compose.yml          # Main orchestration file
├── .env                        # Environment variables for all services
├── api/                        # API service with integrated notification handling logic
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                  # Flask app with MQTT and notifications integration
│   ├── mqtt/                   # MQTT handlers and session management
│   │   ├── mqtt_handler.py     # MQTT connection and message handling
│   │   ├── session_handler.py  # Session state management
│   │   └── test_mqtt_handlers.py # MQTT testing suite
│   └── ...
├── face_recognition_service/   # Face recognition service files/models
│   ├── Dockerfile
│   ├── models/
│   ├── data/
│   └── ...
├── mqtt/                       # MQTT broker configuration files/logs/data
│   ├── mosquitto.conf          # Configuration file for Mosquitto broker
│   ├── data/                   # MQTT persistence data storage directory
│   ├── log/                    # MQTT broker logs directory
│   └── docker-compose.yml      # MQTT broker configuration
├── frontend/                   # React frontend files/components/public assets
│   ├── Dockerfile              # Frontend container definition file
│   ├── public/
│   ├── src/
│   └── ...
├── database/                   # Database initialization scripts.
│   ├── init.sql                # SQL script to initialize pgVector and tables.
```

---

## **Testing MQTT Components**

### **Prerequisites**
1. Install dependencies:
```powershell
pip install -r api/mqtt/requirements.txt
```

2. Start MQTT broker:
```powershell
docker run -d -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

### **Running Tests**
```powershell
python -m pytest api/mqtt/test_mqtt_handlers.py -v
```

### **Test Coverage**
The test suite includes:
1. Basic MQTT connection testing
2. Session creation and management
3. Message handling
4. Proper disconnection

---

## **Docker Compose Configuration**

Save this configuration as `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  api:
    build: ./api/
    ports:
      - "8080:8080"
    environment:
      - FACE_RECOGNITION_SERVICE_URL=http://face_recognition:5001
      - MQTT_BROKER=mqtt://mosquitto:1883
      - DATABASE_URL=postgres://postgres:postgres@postgres:5432/security_db

  face_recognition:
    build: ./face_recognition_service/
    ports:
      - "5001:5001"
    volumes:
      - ./face_recognition_service/models:/app/models/
      - ./face_recognition_service/data:/app/data/

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres 
      POSTGRES_PASSWORD: postgres 
      POSTGRES_DB=security_db

  mosquitto:
    image: eclipse-mosquitto:latest 
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mqtt/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./mqtt/data:/mosquitto/data
      - ./mqtt/log:/mosquitto/log

  frontend-service:
    build: ./frontend/
    ports:
      - "3000:3000"
```

---

## **Simplified Deployment Strategy**

### Local Development Setup

1. Install Docker and Docker Compose.
2. Clone the repository:
```powershell
git clone https://github.com/your-repo/campus-security-system.git && cd campus-security-system/
```
3. Start all services:
```powershell
docker-compose up --build -d
```

### Production Deployment

For production deployment, use Fly.io or AWS ECS to host the services. Ensure proper secret management, health checks, and monitoring are configured.

---

This simplified architecture integrates notifications directly into the API service while maintaining modularity across other services. The MQTT implementation follows a clear topic structure and includes comprehensive testing. 