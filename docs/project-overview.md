# Campus Security Enhancement System (CSES)

## 📁 Project Structure
```
├───api/                 # Flask API service
├───database/           # PostgreSQL with pgvector
├───docs/              # Documentation
├───face_recognition/  # GhostFaceNet service
├───frontend/         # React dashboard
├───mqtt_broker/      # Eclipse Mosquitto
│   ├───config/       # Broker configuration
│   ├───data/         # Message persistence
│   └───log/          # Broker logs
└───notification_service/  # Real-time alerts
```

## 🛠️ Technology Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **API** | Flask (Python) | Authentication & session management |
| **Face Detection** | ESP-WHO | On-device face detection for ESP32-CAM |
| **Face Recognition** | GhostFaceNet | 512D embedding generation |
| **Database** | PostgreSQL + pgvector | Employee records & face embeddings |
| **RFID Processing** | Arduino Uno R4 | RFID tag reading |
| **Communication** | MQTT | Real-time messaging |
| **Frontend** | React.js | Security monitoring dashboard |
| **Notifications** | ntfy (SSE) | Instant security alerts |
| **Deployment** | Docker + fly.io | Containerized deployment |

## 🏗️ System Architecture

### Core Services

#### 1. API Service (`:8080`)
- **Responsibilities**
  - Authentication flow
  - Session management
  - Security operations
  - Service integration
- **Dependencies**
  - Database
  - MQTT Broker
  - Face Recognition

#### 2. Database Service (`:5432`)
- **Features**
  - Employee records
  - Face embeddings
  - Vector similarity search
- **Configuration**
  ```yaml
  user: cses_admin
  database: cses_db
  storage: Docker volumes
  ```

#### 3. MQTT Broker (`:1883`)
- **Channels**
  - `campus/security/session`
  - `campus/security/emergency`
  - `campus/security/unlock`
  - `campus/security/rfid`
- **Features**
  - Message persistence
  - Configurable security
  - Comprehensive logging

### 🐳 Docker Architecture

```yaml
services:
  api:
    build: ./api
    ports: ["8080:8080"]
    networks: [app-network, mqtt-network]
    depends_on: [db, mosquitto]

  db:
    image: ankane/pgvector:latest
    ports: ["5432:5432"]
    networks: [app-network]
    volumes: [postgres_data, init.sql, migrations]

  mosquitto:
    image: eclipse-mosquitto:latest
    ports: ["1883:1883"]
    networks: [mqtt-network, app-network]
    volumes: [config, data, log]
```

### 🔌 Network Configuration
- **app-network**: API ↔ Database communication
- **mqtt-network**: MQTT messaging

### 💾 Volume Management
- **Database**: `postgres_data`
- **MQTT**: 
  - `mosquitto_data`
  - `mosquitto_log`
  - `mosquitto_config`

## 🔄 Data Flow

### Session Flow
1. **RFID Detection** (Arduino)
   - Reads badge
   - Signals ESP32

2. **Session Creation** (ESP32)
     ```json
     {
     "session_id": "unique-id",
     "face_data": "captured_data",
     "rfid_data": "user_or_incomplete",
       "timestamp": "current-time"
     }
     ```

3. **Processing** (API)
   - Receives MQTT payload
   - Validates session
   - Triggers actions

### Emergency Flow
1. **Detection** (Arduino)
   - Emergency signal
   - Immediate unlock
   - Sends MQTT message to `campus/security/emergency`

2. **Processing** (API)
   - Receives MQTT message from `campus/security/emergency`
   - Logs event
   - Stops session processing

3. **Processing** (ESP32)
   - Receives MQTT message from `campus/security/emergency`
   - Suspends face capture and session creation
   - Upon received mqtt message, sets emergency flag to true
   - Continues face capture but does not process sessions

## 🚀 Development

### Local Setup
```powershell
# Start core services
docker-compose up api db mosquitto

# Start specific service
docker-compose up [service_name]

# View logs
docker-compose logs -f [service_name]
```

### Service Dependencies
- API → Database
- API → MQTT
- All services → Docker networks

## 🔒 Security
- Network isolation
- Environment variables
- Persistent storage
- Health monitoring

## 📡 MQTT Channels

### Session Channel
- **Topic**: `campus/security/session`
- **Publisher**: ESP32CAM
- **Subscriber**: API
- **Purpose**: Session payload transmission

### Emergency Channel
- **Topic**: `campus/security/emergency`
- **Publisher**: Arduino
- **Subscriber**: API, ESP32
- **Purpose**: Emergency override

### Unlock Channel
- **Topic**: `campus/security/unlock`
- **Publisher**: API
- **Subscriber**: Arduino
- **Purpose**: Door control

### RFID Channel
- **Topic**: `campus/security/rfid`
- **Publisher**: Arduino
- **Subscriber**: ESP32
- **Purpose**: RFID tag reading
