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

- `campus/security/session` - Receives session data from ESP32-CAM
  ```json
  {
    "device_id": "esp32-cam-01",
    "session_id": "uuid",
    "timestamp": 1234567890,
    "session_duration": 5000,
    "image_size": 1024,
    "image_data": "base64_encoded_image",
    "rfid_detected": true,
    "face_detected": true,
    "free_heap": 20000,
    "state": "SESSION"
  }
  ```
- `campus/security/emergency` - Emergency override channel
- `campus/security/unlock` - Door unlock commands

## Dependencies

See `requirements.txt` for full list of dependencies.

## Development Notes

- The API requires a running PostgreSQL database
- MQTT broker must be available
- Face recognition service should be accessible
- For local development, all services should be running on localhost

## Future Enhancements

### Multi-Session Management (Future)
The API will be updated to support multiple sessions from a single motion event. This feature is planned for future development and includes:

- Enhanced session structure with motion grouping
- New API endpoints for session management
- Automatic session cleanup
- Modified unlock logic for grouped sessions

Note: This enhancement is not currently implemented and should not be considered in current development unless explicitly working on multi-session management. The current implementation supports single-session operation only.

Dependencies:
- ESP32-CAM firmware updates for multi-session support
- Database schema updates
- MQTT payload structure changes
- Face recognition service updates

## FUTURE WORK

### Implementation Location
All implementation changes should be made within the `api` folder structure. This includes:
- API endpoints and routes
- Service integrations
- Data models
- Utility functions
- Tests
- Configuration

The face recognition service and database are separate components that should not be modified directly.

### Milestone 1: Session Processing Integration (Week 1)
- [X] **API Structure Setup**
  ```
  api/
  ├── app.py              # Main Flask application
  ├── routes/
  │   ├── __init__.py
  │   ├── session.py      # Session processing endpoints
  │   └── admin.py        # Manual review endpoints
  ├── services/
  │   ├── __init__.py
  │   ├── face.py         # Face recognition service integration
  │   └── database.py     # Database operations
  ├── models/
  │   ├── __init__.py
  │   └── session.py      # Session data models
  └── utils/
      ├── __init__.py
      └── validation.py   # Input validation helpers
  ```

- [X] **Session Processing Flow**
  - [X] Implement session validation
    - [X] Create session model with required fields
      ```python
      class Session(BaseModel):
          device_id: str
          session_id: str
          timestamp: int
          session_duration: int
          image_size: int
          image_data: str
          rfid_detected: bool
          face_detected: bool
          free_heap: int
          state: str
      ```
    - [X] Add input validation for session data
      - UUID validation for session_id
      - Image size limits (0-10MB)
      - State validation against allowed values
  - [X] Implement session state tracking
    - [X] Create database model for session tracking
      ```python
      class SessionRecord(Base):
          __tablename__ = 'session_records'
          id = Column(UUID, primary_key=True)
          device_id = Column(String, nullable=False)
          state = Column(String, nullable=False)
          start_time = Column(DateTime, nullable=False)
          last_update = Column(DateTime, nullable=False)
          face_detected = Column(Boolean, default=False)
          rfid_detected = Column(Boolean, default=False)
          is_expired = Column(Boolean, default=False)
      ```
    - [X] Implement MQTT message handler
      - [X] Parse incoming session data
      - [X] Validate using Pydantic model
      - [X] Update or create session record
      - [X] Handle state transitions
    - [X] Add session timeout management
      - [X] Set session expiration time
      - [X] Implement cleanup for expired sessions
      - [X] Handle session termination
    - [X] Create session status endpoints
      - [X] GET /api/sessions/active - List active sessions
      - [X] GET /api/sessions/{session_id} - Get session details
      - [X] POST /api/sessions/update - Update session state
    - [X] Add session monitoring
      - [X] Track session duration
      - [X] Monitor state transitions
      - [X] Log session events
  - [X] Add face recognition service integration
    - [X] Create client for `/embed` endpoint
    - [X] Create client for `/verify` endpoint
    - [X] Implement error handling for service failures
  - [X] Create database queries for face matching
    - [X] Add employee lookup by RFID
        - Create `Employee` SQLAlchemy model (map to `employees` table).
        - Add `get_employee_by_rfid(rfid_tag: str)` method to `DatabaseService`.
        - Query `employees` table filtering by `rfid_tag` index.
        - Return `Employee` object including `face_embedding` or `None`.
    - [X] Implement vector similarity search using pgvector
        - Add `pgvector` to `requirements.txt`.
        - Define `face_embedding` column in `Employee` model using `Vector(512)`.
        - Add `find_similar_embeddings(new_embedding: List[float], threshold: float, limit: int)` method to `DatabaseService`.
        - Use `cosine_distance` operator (`<->`) to find closest matches below `threshold`.
        - Order by distance and return top `limit` matches (employee ID, name, distance/confidence).
    - [X] Create verification image storage
        - Create `VerificationImage` SQLAlchemy model (map to `verification_images` table).
        - Define columns matching schema (`session_id`, `image_data` as `LargeBinary`, `matched_employee_id`, etc.).
        - Add `save_verification_image(session_id: str, image_data: bytes, ...)` method to `DatabaseService`.
        - Method saves the provided image data (bytes) and verification metadata.

### Milestone 2: MQTT Integration & Core Verification Logic (Week 2)
- [X] **Implement MQTT Handler Service**
    - [X] Create `services/mqtt_service.py` (or similar).
    - [X] Initialize `paho.mqtt.client`.
    - [X] Add methods to connect/disconnect using `Config` (broker address, port).
    - [X] Implement `on_connect` callback to subscribe to topics.
    - [X] Implement `on_message` callback to route messages.
    - [X] Subscribe to: `campus/security/session`, `campus/security/emergency`.
- [X] **Handle Session Messages (`campus/security/session`)**
    - In `on_message`, if topic is `campus/security/session`:
        - Parse JSON payload.
        - Validate payload using `Session` Pydantic model (from M1).
        - Extract `session_id`, `image_data` (base64), `rfid_detected`, `rfid_tag` (if present), etc.
        - **(Verification Flow Start)**
        - If `image_data` exists: Call `face_client.get_embedding(image_data)` -> `new_embedding`.
        - If `rfid_detected` and `rfid_tag` exists: Call `database_service.get_employee_by_rfid(rfid_tag)` -> `employee_record`.
        - **(Verification Logic)**
        - If `employee_record` and `new_embedding` and `employee_record.face_embedding` exist:
            - Call `face_client.verify_embeddings(new_embedding, employee_record.face_embedding)` -> `verification_result`.
            - Determine `access_granted` based on `verification_result['is_match']` and `verification_result['confidence']` (check against a threshold).
            - Set `verification_method` to 'RFID+FACE'.
        - Else if `new_embedding` exists (and maybe no valid RFID):
            - *Optional: Implement face-only search:* Call `database_service.find_similar_embeddings(new_embedding)` -> `matches`.
            - For now: Set `access_granted = False`, `verification_method` = 'FACE_ONLY_ATTEMPT'.
        - Else if `employee_record` exists (e.g., RFID only, no image):
            - Set `access_granted = False` (require face for now), `verification_method` = 'RFID_ONLY_ATTEMPT'.
        - Else (no RFID, no image, or other error):
             - Set `access_granted = False`, `verification_method` = 'ERROR/INCOMPLETE'.
        - **(Logging & Updates)**
        - Call `database_service.save_verification_image(...)` with image data, session ID, results.
        - Call `database_service.log_access_attempt(...)` (method TBD) with session ID, employee ID (if found), method, granted status, confidence.
        - Update `SessionRecord` in DB via `database_service.update_session(...)` (if needed).
        - If `access_granted`: Publish unlock command to `campus/security/unlock`.
- [X] **Handle Emergency Messages (`campus/security/emergency`)**
    - In `on_message`, if topic is `campus/security/emergency`:
        - Parse JSON payload.
        - Log the emergency event (source, timestamp).
        - Publish unlock command to `campus/security/unlock`.
- [X] **Publish Unlock Messages (`campus/security/unlock`)**
    - Define standard JSON payload (e.g., `{"command": "UNLOCK", "session_id": "..."}`).
    - Implement helper method in MQTT service to publish this message.
    - Call publish method when access granted or emergency occurs.
- [ ] **Integrate MQTT Service into App Startup**
    - Instantiate `MQTTService` in `app.py` after other services.
    - Call `mqtt_service.connect()` to start listening.
    - Implement graceful shutdown (disconnect).
- [X] **Basic API Health Check Passing**
    - [X] API is running and accessible at `http://localhost:8080`.
    - [X] `GET /` health check endpoint returns a successful status.

### Milestone 3: Identity Verification (Week 3)
- [X] **Face Recognition Integration**
  - [X] Connect to existing face recognition service
  - [X] Use GhostFaceNets model for embeddings
  - [X] Implement image preprocessing
  - [X] Handle base64 image encoding/decoding
  - [X] Implement face embedding generation
  - [ ] Store embeddings in database
  - [X] Add face matching logic using pgvector
  - [X] Set confidence thresholds

- [X] **RFID Integration**
  - [X] Add RFID
  - [X] Implement RFID-face matching
  - [X] Verify face matches RFID owner
  - [X] Handle mismatches
  - [X] Create combined verification logic

- [ ] **Notification Integration**
  - [ ] Add notification functions to API routes
  - [ ] Add notification triggers for authentication
  - [ ] Create notification history table
    - [ ] Add notification_history schema
    - [ ] Implement notification logging
    - [ ] Add notification retrieval endpoints

### Milestone 4: Access Control (Week 4)
- [ ] **Verification Methods**
  - [ ] Implement RFID-only verification
    - [ ] Validate RFID tag
    - [ ] Check employee access rights
    - [ ] Log RFID-only access
  - [ ] Add face-only verification
    - [ ] Process face image
    - [ ] Match against database
    - [ ] Log face-only access
  - [ ] Create RFID+face combined verification
    - [ ] Require both verifications
    - [ ] Handle verification order
    - [ ] Log combined access
  - [ ] Add emergency override handling
    - [ ] Implement emergency mode
    - [ ] Handle emergency access
    - [ ] Log emergency events

- [ ] **Access Logging**
  - [ ] Create access log entries
    - [ ] Log all access attempts
    - [ ] Track verification methods
    - [ ] Record timestamps
  - [ ] Add verification method tracking
    - [ ] Log verification type
    - [ ] Record confidence scores
    - [ ] Track verification success
  - [ ] Implement confidence score logging
    - [ ] Store confidence values
    - [ ] Track confidence trends
    - [ ] Flag low confidence events
  - [ ] Add image storage for verification
    - [ ] Store verification images
    - [ ] Implement image cleanup
    - [ ] Handle image retrieval

- [ ] **Access Control Notifications**
  - [ ] Emergency override notifications
    - [ ] Emergency mode activation - HIGH priority
    - [ ] Unauthorized access attempt - HIGH priority
    - [ ] Door left open warning - MEDIUM priority
  - [ ] System status notifications
    - [ ] Service disruption - HIGH priority
    - [ ] Database connection failure - HIGH priority
    - [ ] Face recognition service unavailable - HIGH priority

### Milestone 5: Manual Review System (Week 5)
- [ ] **Admin Interface**
  - [ ] Create session review endpoints
    - [ ] List pending sessions
    - [ ] View session details
    - [ ] Approve/deny access
  - [ ] Add image viewing capabilities
    - [ ] View verification images
    - [ ] Compare face matches
    - [ ] Download images
  - [ ] Implement verification override
    - [ ] Force access approval
    - [ ] Override verification
    - [ ] Add override reason
  - [ ] Add admin audit logging
    - [ ] Log admin actions
    - [ ] Track overrides
    - [ ] Monitor admin access

- [ ] **Admin Notifications**
  - [ ] Manual review notifications
    - [ ] Pending review alerts - MEDIUM priority
    - [ ] Review completion notifications
  - [ ] Admin action notifications
    - [ ] Override actions - MEDIUM priority
    - [ ] System configuration changes
  - [ ] Notification dashboard
    - [ ] Create notification history endpoint
    - [ ] Add notification filtering
    - [ ] Implement notification status tracking

- [ ] **Cleanup and Optimization**
  - [ ] Implement image cleanup
    - [ ] Use existing cleanup function
    - [ ] Schedule cleanup tasks
    - [ ] Monitor storage usage
  - [ ] Add performance monitoring
    - [ ] Track response times
    - [ ] Monitor memory usage
    - [ ] Log performance metrics
  - [ ] Create maintenance endpoints
    - [ ] System status checks
    - [ ] Database maintenance
    - [ ] Service health
  - [ ] Add system health checks
    - [ ] Monitor all services
    - [ ] Check database health
    - [ ] Verify face recognition

### Existing Components
- **Face Recognition Service**
  - Containerized service with `/embed` and `/verify` endpoints
  - Uses GhostFaceNets model for face embeddings
  - Handles image preprocessing and embedding generation
  - Provides confidence scores for matches

- **Database Structure**
  - PostgreSQL with pgvector extension
  - Tables:
    - `employees`: Stores employee data and face embeddings
    - `access_logs`: Records access attempts and results
    - `verification_images`: Stores verification images and metadata
  - Indexes for efficient querying
  - Automatic cleanup of old verification images

- **Notification Service**
  - SMS notifications via Twilio
  - ntfy integration for dashboard display
  - Notification history storage
  - Priority-based delivery (HIGH/MEDIUM/LOW)
  - Immediate notification dispatch

### Implementation Notes
1. Leverage existing face recognition service for embedding generation
2. Use pgvector for efficient face matching in database
3. Implement simple session state machine
4. Focus on core functionality before adding features
5. Maintain clear separation of concerns
6. Use existing database schema without modifications
7. Keep manual review system simple and focused
8. Keep notifications focused on critical security events
9. Integrate notifications directly into API routes
10. Maintain notification history for dashboard display

## Technical Specifications

### API Endpoints

#### Session Processing (`api/routes/session.py`)
```python
# POST /api/session/start
{
    "device_id": "esp32-cam-01",
    "session_id": "uuid",
    "image_data": "base64_encoded_image",
    "rfid_tag": "NT2025001"
}

# POST /api/session/verify
{
    "session_id": "uuid",
    "verification_method": "FACE|RFID|BOTH",
    "confidence": 0.95
}

# GET /api/session/{session_id}
{
    "session_id": "uuid",
    "status": "PENDING|APPROVED|DENIED",
    "verification_method": "FACE|RFID|BOTH",
    "confidence": 0.95,
    "created_at": "timestamp",
    "updated_at": "timestamp"
}
```

#### Face Recognition Integration (`api/services/face.py`)
```python
# POST /api/face/embed
{
    "image": "base64_encoded_image"
}

# POST /api/face/verify
{
    "embedding1": [0.1, 0.2, ...],
    "embedding2": [0.1, 0.2, ...]
}
```

#### Database Operations (`api/services/database.py`)
```python
# Employee Lookup
def get_employee_by_rfid(rfid_tag: str) -> Dict:
    """
    Returns:
        {
            "id": "uuid",
            "name": "string",
            "rfid_tag": "string",
            "role": "string",
            "face_embedding": [float],
            "active": bool
        }
    """

# Face Matching
def find_face_match(embedding: List[float], threshold: float = 0.8) -> Dict:
    """
    Returns:
        {
            "employee_id": "uuid",
            "confidence": float,
            "name": "string"
        }
    """
```

#### Notification Endpoints (`api/routes/notifications.py`)
```python
# POST /api/notifications
{
    "message": "string",
    "severity": "HIGH|MEDIUM|LOW",
    "source": "string",
    "recipients": ["string"]
}

# GET /api/notifications/history
{
    "notifications": [
        {
            "id": "uuid",
            "message": "string",
            "severity": "string",
            "source": "string",
            "timestamp": "datetime",
            "recipients": ["string"]
        }
    ],
    "total": 25,
    "page": 1,
    "per_page": 10
}
```

### Test Plan

#### 1. Face Recognition Service Tests
Location: `face_recognition/tests/`
```python
# test_embedding.py
def test_embedding_generation():
    """Test face embedding generation with sample images"""
    # Test with valid face image
    # Test with no face image
    # Test with multiple faces
    # Test with poor quality image

# test_verification.py
def test_face_verification():
    """Test face verification with known matches"""
    # Test same person different images
    # Test different people
    # Test confidence thresholds
    # Test error handling
```

#### 2. Session Processing Tests
Location: `api/tests/`
```python
# test_session.py
def test_session_flow():
    """Test complete session processing flow"""
    # Test session creation
    # Test face verification
    # Test RFID verification
    # Test combined verification
    # Test session timeout
    # Test error handling

# test_verification.py
def test_verification_methods():
    """Test different verification methods"""
    # Test face-only verification
    # Test RFID-only verification
    # Test combined verification
    # Test emergency override
```

#### 3. Database Integration Tests
Location: `api/tests/`
```python
# test_database.py
def test_employee_lookup():
    """Test employee database operations"""
    # Test RFID lookup
    # Test face matching
    # Test access logging
    # Test image storage

# test_cleanup.py
def test_cleanup_functions():
    """Test database cleanup operations"""
    # Test verification image cleanup
    # Test old session cleanup
    # Test access log retention
```

#### 4. Performance Tests
Location: `api/tests/`
```python
# test_performance.py
def test_response_times():
    """Test API response times"""
    # Test face embedding generation time
    # Test face matching time
    # Test database query times
    # Test session processing time

# test_concurrency.py
def test_concurrent_requests():
    """Test system under load"""
    # Test multiple simultaneous sessions
    # Test database connection pool
    # Test service availability
```

#### 5. Security Tests
Location: `api/tests/`
```python
# test_security.py
def test_access_control():
    """Test security measures"""
    # Test authentication
    # Test authorization
    # Test input validation
    # Test error handling

# test_audit.py
def test_audit_logging():
    """Test audit logging"""
    # Test access log entries
    # Test admin actions
    # Test verification attempts
    # Test system changes
```

#### 6. Notification Service Tests
Location: `api/tests/`
```python
# test_notifications.py
def test_notification_sending():
    """Test notification dispatch"""
    # Test SMS notifications
    # Test ntfy integration
    # Test notification formatting
    # Test recipient handling

def test_notification_history():
    """Test notification storage and retrieval"""
    # Test notification logging
    # Test history retrieval
    # Test filtering and pagination
```

### Testing Environment Setup
```powershell
# Create test database
docker-compose -f database/docker-compose.yml up -d
psql -U cses_admin -d cses_db -f database/init.sql
psql -U cses_admin -d cses_db -f database/sample_data.sql

# Start face recognition service
docker-compose -f face_recognition/docker-compose.yml up -d

# Run tests
pytest api/tests/ -v
pytest face_recognition/tests/ -v
```

### Test Data
Location: `api/tests/data/`