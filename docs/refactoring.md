# Refactoring the codebase

## Clear Project Structure
```
cses/                           # Root directory (rename from Senior Capstone)
├── services/                   # All microservices
│   ├── api/                   # Flask API (existing)
│   ├── face_recognition/      # Face recognition service
│   ├── mqtt_broker/          # MQTT broker config
│   └── database/             # Database migrations and scripts
├── hardware/                  # All hardware-related code
│   ├── esp32-cam/            # ESP32 code (renamed from ESP32-WROVER)
│   ├── controller/           # Arduino Mega code (renamed from ArduinoMega)
│   └── servo/                # Arduino Uno code (renamed from ServoArduinoUno)
├── docs/                     # Project documentation
│   ├── api/                 # API documentation
│   ├── hardware/           # Hardware documentation
│   ├── deployment/        # Deployment guides
│   └── wireframes/       # UI/UX wireframes
├── scripts/               # Utility scripts
├── tests/                # System-level integration tests
├── .gitignore           # Git ignore file
├── docker-compose.yml   # Main docker compose file
└── README.md           # Project overview
```

## Service-Based Architecture

```
services/
├── api/
│   ├── app.py
│   ├── routes/
│   └── models/
├── face_recognition/
│   ├── face_recognition.py
│   ├── models/
│   └── utils/
├── mqtt_broker/
│   ├── config.py
│   └── mqtt_broker.py
├── database/
│   ├── models/
│   ├── migrations/
│   └── utils/
├── hardware/
│   ├── esp32-cam/
│   ├── controller/
│   └── servo/

```

## Hardware-Based Architecture
