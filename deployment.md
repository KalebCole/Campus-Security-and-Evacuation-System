# Campus Security and Evacuation System - Deployment & Architecture

This document outlines the deployment architecture, local development setup, and production strategy for the Campus Security and Evacuation System.

## System Architecture

### Modular Service Breakdown

| Service Name | Description | Technology | Container Name |
|--------------|-------------|------------|----------------|
| `campus-api-service` | Core API service with MobileFaceNet for embedding generation | Flask | `campus-api` |
| `mqtt-broker` | Message broker for device communication | Eclipse Mosquitto | `campus-mqtt` |
| `database-service` | Database with pgvector for face embeddings | Supabase | (managed externally) |
| `frontend-service` | Security monitoring dashboard | React | `campus-frontend` |
| `grafana-service` | Metrics visualization | Grafana | `campus-grafana` |
| `notification-service` | Real-time notification delivery | ntfy | `campus-notify` |

### Architecture Diagram

```
                           ┌─────────────────┐
                           │  Security Admin │
                           │    Interface    │
                           └────────┬────────┘
                                    │
                                    ▼
┌─────────────────┐     MQTT     ┌─────────────────┐     pgvector    ┌─────────────────┐
│   Arduino Uno   │◄──────────►│    MQTT Broker   │                │   Supabase DB   │
│   RFID Client   │             └────────┬────────┘◄──────────────►│   (PostgreSQL)  │
└─────────────────┘                      │                         └─────────────────┘
                                         │                                  ▲
┌─────────────────┐     MQTT             │                                  │
│    ESP32-CAM    │◄───────────┐         │                                  │
│  (ESP-WHO det.) │            ▼         ▼                                  │
└─────────────────┘     ┌─────────────────┐                                 │
                        │   API Service   │                                 │
                        │ (MobileFaceNet) │◄────────────────────────────────┘
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │     Grafana     │
                        │    Monitoring   │
                        └─────────────────┘
```

## Container Organization

The system uses Docker containers for all backend services, organized in a hierarchical structure:

```
campus-security-system/
├── docker-compose.yml          # Main orchestration file
├── .env                        # Environment variables for all services
├── server/                     # API service with MobileFaceNet
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── ...
├── mqtt/                       # MQTT broker configuration
│   ├── Dockerfile
│   ├── mosquitto.conf
│   └── ...
├── frontend/                   # React frontend (when implemented)
│   ├── Dockerfile
│   └── ...
└── monitoring/                 # Grafana dashboards
    ├── Dockerfile
    └── ...
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
  campus-api:
    build:
      context: ./server
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    volumes:
      - ./server:/app
      - ./data:/data
    environment:
      - FLASK_ENV=development
      - FLASK_APP=app.py
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - MQTT_BROKER=campus-mqtt
      - MQTT_PORT=1883
      - MQTT_USERNAME=${MQTT_USERNAME}
      - MQTT_PASSWORD=${MQTT_PASSWORD}
    depends_on:
      - campus-mqtt
    networks:
      - campus-net
    restart: unless-stopped

  campus-mqtt:
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"  # MQTT
      - "9001:9001"  # WebSockets
    volumes:
      - ./mqtt/config:/mosquitto/config
      - ./mqtt/data:/mosquitto/data
      - ./mqtt/log:/mosquitto/log
    networks:
      - campus-net
    restart: unless-stopped

  campus-notify:
    image: binwiederhier/ntfy
    ports:
      - "8080:80"
    volumes:
      - ./ntfy/cache:/var/cache/ntfy
      - ./ntfy/etc:/etc/ntfy
    networks:
      - campus-net
    restart: unless-stopped

  campus-grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - ./grafana/data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    networks:
      - campus-net
    restart: unless-stopped

networks:
  campus-net:
    driver: bridge
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

### Server Dockerfile

Create a multi-stage Dockerfile for the server component at `server/Dockerfile`:

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

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
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

# Grafana Configuration
GRAFANA_ADMIN=admin
GRAFANA_PASSWORD=secure-password-here
```

### Starting the Local Environment

Run the following commands to initialize and start all services:

```bash
# Create required directories
mkdir -p mqtt/config mqtt/data mqtt/log ntfy/cache ntfy/etc grafana/data grafana/provisioning

# Copy the Mosquitto config
cp mqtt/config/mosquitto.conf mqtt/config/

# Start all services
docker-compose up --build
```

## Production Deployment Strategy (fly.io)

### Containerization for Production

For production deployment, the containers will be optimized for size and security:

1. Remove development dependencies
2. Use multi-stage builds for all services
3. Pin all dependency versions
4. Implement proper secret management
5. Configure health checks and restart policies

### Service Deployment

#### 1. API Service Deployment

Create a `fly.toml` file in the server directory:

```toml
app = "campus-security-api"

[build]
  dockerfile = "Dockerfile.prod"

[env]
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true

[http_service.concurrency]
  type = "connections"
  hard_limit = 100
  soft_limit = 80

[[services.ports]]
  port = 80
  handlers = ["http"]

[[services.ports]]
  port = 443
  handlers = ["tls", "http"]

[services.http_checks]
  interval = "30s"
  timeout = "5s"
  grace_period = "10s"
  method = "GET"
  path = "/api/test"
  protocol = "http"
  tls_skip_verify = false
```

Deploy with:

```bash
cd server
fly launch
```

#### 2. MQTT Broker Deployment

Create a dedicated app for the MQTT broker:

```bash
cd mqtt
fly launch --name campus-security-mqtt
```

Configure TLS for the MQTT broker in production using fly.io's certificate management:

```toml
# mqtt/fly.toml
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

[[services.ports]]
  port = 8883
  handlers = ["tls"]
```

### Supabase Configuration with pgvector

The Supabase setup requires the pgvector extension for face embedding storage and similarity search:

1. Create a Supabase project through the web interface
2. Enable the pgvector extension via the SQL Editor:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create employees table with face embedding vector
CREATE TABLE employees (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  rfid_tag TEXT UNIQUE,
  face_embedding VECTOR(128), -- 128D vector for MobileFaceNet embeddings
  role TEXT,
  email TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  active BOOLEAN DEFAULT TRUE
);

-- Create index for similarity search
CREATE INDEX ON employees 
USING ivfflat (face_embedding vector_cosine_ops)
WITH (lists = 100);

-- Create access logs table
CREATE TABLE access_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  employee_id UUID REFERENCES employees(id),
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  access_granted BOOLEAN,
  verification_method TEXT,
  similarity_score REAL,
  session_id TEXT
);

-- Create notifications table
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  type TEXT NOT NULL,
  severity TEXT NOT NULL,
  message TEXT NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  related_employee_id UUID REFERENCES employees(id),
  acknowledged BOOLEAN DEFAULT FALSE
);
```

### Secrets Management

Store sensitive configuration in fly.io secrets:

```bash
fly secrets set SUPABASE_URL=your-supabase-url \
                SUPABASE_KEY=your-supabase-anon-key \
                MQTT_USERNAME=production-username \
                MQTT_PASSWORD=production-password
```

## ESP32-CAM Configuration

The ESP32-CAM requires specific configuration for the ESP-WHO framework and MQTT communication:

### Development Setup

1. Install ESP-IDF and ESP-WHO following the official guidelines
2. Configure the ESP32-CAM for face detection:

```c
// ESP-WHO face detection configuration
face_detection_config_t config = {
    .extract_embeddings = false,  // We don't need embeddings on the device
    .model_selection = FACE_DET_BASIC,  // Use basic model to save memory
    .confidence_threshold = 0.6,  // Adjust based on your needs
    .roi_x = 0,
    .roi_y = 0,
    .roi_w = 320,
    .roi_h = 240
};
```

3. Configure MQTT connection:

```c
// MQTT configuration
const char* mqtt_server = "your-mqtt-broker";
const int mqtt_port = 1883;
const char* mqtt_user = "device-username";
const char* mqtt_password = "device-password";
const char* mqtt_topic = "campus/security/face";
```

### Production Configuration

For production, update the ESP32-CAM firmware to connect securely to the cloud MQTT broker:

```c
// Production MQTT configuration
const char* mqtt_server = "campus-security-mqtt.fly.dev";
const int mqtt_port = 8883;  // TLS port
const char* mqtt_user = "production-device-username";
const char* mqtt_password = "production-device-password";
const char* mqtt_topic = "campus/security/face";

// Add root CA certificate for TLS
const char* root_ca PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
... Your fly.io root certificate ...
-----END CERTIFICATE-----
)EOF";
```

## MQTT Topic Structure

The system uses a hierarchical MQTT topic structure:

| Topic | Description | Example Payload |
|-------|-------------|----------------|
| `campus/security/device/{device_id}/status` | Device status updates | `{"status":"online","battery":85}` |
| `campus/security/face/{device_id}` | Face images from ESP32-CAM | Binary JPEG image data |
| `campus/security/rfid/{device_id}` | RFID tag readings | `{"rfid_tag":"123456","timestamp":"2023-04-05T12:34:56Z"}` |
| `campus/security/command/{device_id}` | Commands to devices | `{"command":"capture","params":{"quality":80}}` |
| `campus/security/result/{device_id}` | Access verification results | `{"access":"granted","user":"John Doe","confidence":0.92}` |
| `campus/security/system/status` | System-wide status updates | `{"active":true,"devices_online":3}` |

## Monitoring and Observability

The system includes comprehensive monitoring using Grafana:

1. **Operational Metrics**:
   - API request rates and latencies
   - MQTT message throughput
   - Face recognition accuracy
   - Authentication success/failure rates

2. **Infrastructure Metrics**:
   - Container resource usage
   - Network traffic
   - Disk usage for persistent volumes

3. **Business Metrics**:
   - Access patterns by time/location
   - Employee presence statistics
   - Unauthorized access attempts

## Disaster Recovery

### Backup Strategy

1. **Database Backups**:
   - Automated daily backups of Supabase
   - Point-in-time recovery configuration
   - Scheduled backup verification

2. **Configuration Backups**:
   - Git-based configuration management
   - Container image versioning
   - Infrastructure-as-code for deployment configuration

### Recovery Procedures

1. **Database Recovery**:
   - Restore from latest Supabase backup
   - Verify data integrity post-restore
   - Run data migration scripts if needed

2. **Service Recovery**:
   - Deploy containers from verified images
   - Restore configuration from Git repository
   - Validate system functionality with test suite 