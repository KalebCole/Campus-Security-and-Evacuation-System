# Campus Security and Evacuation System - Deployment & Architecture

This document outlines the deployment architecture, local development setup, and production strategy for the Campus Security and Evacuation System.

## System Architecture

### Modular Service Breakdown

| Service Name            | Description                                    | Technology         | Container Name         |
|-------------------------|------------------------------------------------|--------------------|------------------------|
| `api`                   | Core API service for authentication workflows | Flask              | `api`                  |
| `mqtt_handler`          | MQTT message handling and session management  | Python             | `mqtt_handler`         |
| `face_recognition`      | Face recognition service using GhostFaceNet   | Python             | `face_recognition`     |
| `database`              | PostgreSQL with pgVector for embeddings       | PostgreSQL         | `postgres`             |
| `mqtt-broker`           | Message broker for device communication       | Eclipse Mosquitto  | `mosquitto`            |
| `frontend-service`      | Security monitoring dashboard                 | React              | `frontend-service`     |
| `notification-service`  | Real-time notification delivery               | Twilio integration | `notifications`        |

### Architecture Diagram

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
                        │   MQTT Handler  │                                 │
                        │ (Session Mgmt)  │◄────────────────────────────────┘
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Frontend UI    │
                        └─────────────────┘
```

## Container Organization

The system uses Docker containers for all backend services, organized in a hierarchical structure:

```
campus-security-system/
├── docker-compose.yml          # Main orchestration file
├── .env                        # Environment variables for all services
├── api/                        # API service with MQTT handler
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── mqtt/
│   │   ├── mqtt_handler.py    # MQTT message handling
│   │   ├── session_handler.py # Session management
│   │   └── rfid_handler.py    # RFID processing
│   └── ...
├── face_recognition_service/   # Face recognition service files/models
│   ├── Dockerfile
│   ├── models/
│   ├── data/
│   └── ...
├── mqtt/                       # MQTT broker configuration files/logs/data
│   ├── mosquitto.conf          # Configuration file for Mosquitto broker
│   ├── data/                   # MQTT persistence data
│   └── log/                    # MQTT broker logs
├── frontend/                   # React frontend files/components/public assets
│   ├── Dockerfile
│   ├── public/
│   ├── src/
│   └── ...
├── notifications/              # Notification service files/codebase
│   ├── Dockerfile
│   └── notification_service.py
└── database/                   # Database initialization scripts
    ├── init.sql               # SQL script to initialize pgVector and tables
    └── migrations/            # Database migration scripts
```

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Git
- Arduino IDE or PlatformIO (for hardware development)
- ESP-IDF with ESP-WHO framework (for ESP32-CAM development)

### Docker Compose Setup

Save this configuration as `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "8080:8080"
    environment:
      - FACE_RECOGNITION_SERVICE_URL=http://face_recognition:5001
      - MQTT_BROKER=mqtt://mosquitto:1883
      - DATABASE_URL=postgres://postgres:postgres@postgres:5432/security_db
      - FRONTEND_URL=http://frontend-service:3000
    depends_on:
      - face_recognition
      - postgres
      - mosquitto

  face_recognition:
    build: ./face_recognition_service/
    ports:
      - "5001:5001"
    volumes:
      - ./face_recognition_service/models:/app/models/
      - ./face_recognition_service/data:/app/data/
    environment:
      - MODEL_PATH=/app/models/ghostfacenets.h5

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: security_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  mosquitto:
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mqtt/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./mqtt/data:/mosquitto/data
      - ./mqtt/log:/mosquitto/log
    command: mosquitto -c /mosquitto/config/mosquitto.conf

  frontend-service:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://api:8080

  notifications:
    build: ./notifications
    environment:
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}

volumes:
  postgres_data:
```

### MQTT Broker Configuration

Create a basic Mosquitto configuration at `mqtt/config/mosquitto.conf`:

```
# Basic configuration for local development
listener 1883
allow_anonymous true

persistence true
persistence_location /mosquitto/data/

log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
```

For production, a more secure configuration will be used with authentication and TLS.

### API Dockerfile

Create a multi-stage Dockerfile for the API component at `api/Dockerfile`:

```dockerfile
# Build stage for MobileFaceNet dependencies
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/build/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/*

# Copy application code
COPY . .

# Setup environment
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]
```

### Environment Configuration

Create a `.env` file in the project root with these variables:

```
# Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key

# MQTT Configuration
MQTT_USERNAME=campus-system
MQTT_PASSWORD=strong-password-here

# Notification Configuration
NTFY_TOPIC=campus-security-alerts
```

### Starting the Local Environment

Run the following commands to initialize and start all services:

```bash
# Create required directories
mkdir -p mqtt/config mqtt/data mqtt/log ntfy/cache ntfy/etc

# Copy the Mosquitto config
cp mqtt/config/mosquitto.conf mqtt/config/

# Start all services
docker-compose up --build
```

## Production Deployment (Fly.io)

### Overview
For the capstone project presentation, we'll deploy the core services on Fly.io. This deployment will be a simple, single-instance setup sufficient for demonstration purposes.

### Core Services to Deploy
1. API Service (Flask)
2. MQTT Broker (Mosquitto)
3. PostgreSQL Database (Supabase)

### Deployment Steps

#### 1. API Service Deployment

Create a `fly.toml` file in the api directory:

```toml
app = "campus-security-api"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8080"
  FACE_RECOGNITION_SERVICE_URL = "http://face_recognition:5001"
  MQTT_BROKER = "mqtt://campus-security-mqtt:1883"
  DATABASE_URL = "postgres://postgres:postgres@campus-security-db:5432/security_db"

[http_service]
  internal_port = 8080
  force_https = true

[[services.ports]]
  port = 80
  handlers = ["http"]

[[services.ports]]
  port = 443
  handlers = ["tls", "http"]
```

Deploy with:
```bash
cd api
fly launch
```

#### 2. MQTT Broker Deployment

Create a `fly.toml` file in the mqtt directory:

```toml
app = "campus-security-mqtt"

[build]
  dockerfile = "Dockerfile"

[env]
  MOSQUITTO_CONF_DIR = "/etc/mosquitto"

[mounts]
  source = "mosquitto_data"
  destination = "/mosquitto/data"

[[services.ports]]
  port = 1883
  handlers = []
```

Deploy with:
```bash
cd mqtt
fly launch
```

#### 3. Database Setup

For the presentation, we'll use Supabase's free tier:
1. Create a new project at https://supabase.com
2. Run the initialization SQL from `database/init.sql`
3. Get the connection details and update the API service's environment variables

### Environment Variables

Set the required environment variables in Fly.io:

```bash
# For the API service
fly secrets set \
  SUPABASE_URL=your-supabase-url \
  SUPABASE_KEY=your-supabase-anon-key \
  MQTT_USERNAME=demo \
  MQTT_PASSWORD=demo-password
```

### Testing the Deployment

1. Verify API service:
```bash
curl https://campus-security-api.fly.dev/health
```

2. Test MQTT connection:
```bash
mosquitto_pub -h campus-security-mqtt.fly.dev -p 1883 -t "test" -m "hello"
```

3. Verify database connection through the API endpoints

### Presentation Setup

For the capstone presentation:
1. Have the ESP32-CAM and Arduino Uno R4 pre-configured with the Fly.io MQTT broker address
2. Test the complete authentication flow before the presentation
3. Prepare a backup local setup in case of network issues during the presentation