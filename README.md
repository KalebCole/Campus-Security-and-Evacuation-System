# Campus Security and Evacuation System

Access control and security monitoring system using facial recognition and RFID authentication.

## Overview

System that combines motion detection, facial recognition, and RFID authentication to control access and monitor security events.

### Architecture
- ESP32-CAM for image capture and processing
- Arduino R4 WiFi for system control
- Flask server for authentication and notifications
- Web dashboard for monitoring
- Push notification system for alerts

## Prerequisites
- PlatformIO
- Python 3.9+
- Flask
- Redis
- Supabase account
- ntfy.sh account

## Installation

### Hardware Setup
```bash
# Install PlatformIO
pip install platformio

# Build firmware
pio run
```

### Server Setup
```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env
```

### Usage

#### Running the Server
```bash
python server/app.py
```

### Project Structure
```plaintext
├── diagrams             # System diagrams
├── server               # Flask server
│   ├── app.py           # Main server application
│   ├── config.py        # Configuration settings
│   ├── supabase_client.py      # Supabase client
│   ├── models           # Data models
│   ├── routes           # API routes
│   ├── utils            # Utility functions

```