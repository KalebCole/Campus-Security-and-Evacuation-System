# Campus Security and Evacuation System - Project Status

**Date: April 5, 2025**

## Current System Architecture

### Server Component
- Flask-based API server with verification endpoints
- TensorFlow face recognition model (553MB) causing dependency issues
- Session-based verification workflow connecting RFID and image data
- JSON-based notification system instead of proper database
- Partial Supabase integration with minimal functionality

### Hardware Components
- **Arduino Uno R4 Client**:
  - RFID tag reading with state machine architecture
  - HTTP-based communication with server
  - Error handling and recovery mechanisms
  - Mock RFID data for testing

- **ESP32-CAM Client**:
  - Basic MicroPython implementation
  - Image capture capabilities
  - Web streaming interface
  - Limited integration with verification flow

### Current Technical Bottlenecks
1. **Face Recognition Issues**:
   - Oversized TensorFlow model (553MB) difficult to deploy
   - Python 3.11 compatibility issues
   - Server-side processing creating verification latency

2. **Communication Limitations**:
   - HTTP-based approach lacks real-time capabilities
   - No standardized message format between components
   - Development reliance on ngrok for testing

3. **Database Implementation**:
   - References to user data exist but no structured tables
   - Storage of notification data in JSON files
   - Partial use of Supabase storage for photo URLs
   - No proper event logging or access tracking

## Planned Updates

### Edge Computing Transformation
- Replace TensorFlow with ESP-WHO framework
- Move face recognition to ESP32-CAM
- Implement MSRCR for improved low-light performance
- Reduce bandwidth requirements and server load

### Communication Protocol Upgrade
- Replace HTTP with MQTT for all device communication
- Standardize message format for system events
- Implement publish/subscribe pattern for real-time updates

### Database Structure Implementation
- **Users/Employees Table**:
  ```
  - id (UUID)
  - name (String)
  - rfid_tag (String, unique)
  - photo_url (String) - Supabase storage link
  - embedding (JSON/Array) - Face recognition data
  - is_in_building (Boolean) - Presence status
  - job_title (String)
  - is_active (Boolean)
  - created_at (Timestamp)
  ```

- **Access Events Table**:
  ```
  - id (UUID)
  - user_id (Foreign key)
  - event_type (entry, exit, denied)
  - timestamp (Timestamp)
  - verification_method (rfid, face, both)
  - verification_success (Boolean)
  - location (String, optional)
  ```

- **Notifications Table**:
  ```
  - id (UUID)
  - type (unauthorized_entry, system_alert, etc.)
  - message (String)
  - related_user_id (Foreign key, nullable)
  - image_url (String, optional)
  - is_read (Boolean)
  - timestamp (Timestamp)
  ```

### Frontend Development
- React-based monitoring dashboard for security personnel
- Employee database management (CRUD operations)
- Real-time notifications via ntfy with Server-Sent Events
- Grafana integration for metrics visualization

### Deployment Strategy
- Containerize server for fly.io deployment (zero-cost)
- Implement Docker for local development
- Set up proper environment configuration

## Implementation Timeline

### Phase 1: Backend & Database (By April 9)
1. Complete Supabase database implementation
   - Create tables and indexes
   - Implement repository pattern for data access
   - Migrate from JSON to database storage

2. Update model implementation
   - Replace TensorFlow with ESP-WHO framework
   - Move face recognition to ESP32-CAM
   - Implement MSRCR for low-light enhancement

3. Implement MQTT communication
   - Set up MQTT broker
   - Update Arduino client for MQTT
   - Add publish/subscribe patterns to server

### Phase 2: Frontend & Integration (By April 17)
1. Develop React monitoring dashboard
   - Employee management interface
   - Real-time event visualization
   - Security alerts and notifications

2. Set up notification system
   - Implement ntfy for real-time alerts
   - Connect MQTT events to notification system
   - Add read/unread status tracking

3. Implement system monitoring
   - Set up Grafana dashboards
   - Configure metrics collection
   - Create visualization for access events

This plan transforms the current implementation into a modern, scalable security system with edge computing capabilities and proper database structure, designed for demonstration on a single doorway setup with approximately 20 test users. 