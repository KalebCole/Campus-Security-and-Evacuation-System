# CSES API Service

## Local Development Setup

### Option 1: Using Python Virtual Environment

1. Create and activate virtual environment:
```powershell
# Create venv
python -m venv venv

# Activate venv (Windows PowerShell)
.\venv\Scripts\Activate

# If you get a security error, you might need to run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Create a `.env.development` file in the api directory:
```env
# Local Development Settings
DATABASE_URL=postgresql://cses_admin:cses_password_123!@localhost:5432/cses_db
MQTT_BROKER_ADDRESS=localhost
MQTT_BROKER_PORT=1883
FACE_RECOGNITION_URL=http://localhost:5001
DEBUG=true
```

4. Run the application:
```powershell
python app.py
```

The API will be available at `http://localhost:8080`

### Option 2: Using Docker

1. Build the container:
```powershell
docker build -t cses-api .
```

2. Run the container:
```powershell
# Using the main .env file
docker run -p 8080:8080 --env-file ../.env cses-api

# OR using local development settings
docker run -p 8080:8080 --env-file .env.development cses-api
```

## Testing

Run unit tests:
```powershell
# In virtual environment
pytest tests/

# With coverage report
pytest --cov=app tests/
```

## API Endpoints

- `GET /` - Health check endpoint
- `POST /api/emergency` - Emergency override endpoint

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection URL | - |
| MQTT_BROKER_ADDRESS | MQTT broker host | localhost |
| MQTT_BROKER_PORT | MQTT broker port | 1883 |
| FACE_RECOGNITION_URL | Face recognition service URL | http://localhost:5001 |
| DEBUG | Enable debug mode | false |

## MQTT Topics

- `campus/security/session` - Receives session data
- `campus/security/emergency` - Emergency override channel
- `campus/security/unlock` - Door unlock commands

## Dependencies

See `requirements.txt` for full list of dependencies.

## Development Notes

- The API requires a running PostgreSQL database
- MQTT broker must be available
- Face recognition service should be accessible
- For local development, all services should be running on localhost
