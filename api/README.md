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

### Milestone 1: Session Processing Integration (Week 1)
- [ ] **API Structure Setup**
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

- [ ] **Session Processing Flow**
  - [ ] Implement session validation
    - [ ] Create session model with required fields
    - [ ] Add input validation for session data
    - [ ] Implement session state tracking
  - [ ] Add face recognition service integration
    - [ ] Create client for `/embed` endpoint
    - [ ] Create client for `/verify` endpoint
    - [ ] Implement error handling for service failures
  - [ ] Create database queries for face matching
    - [ ] Implement vector similarity search using pgvector
    - [ ] Add employee lookup by RFID
    - [ ] Create verification image storage
  - [ ] Implement session state tracking
    - [ ] Track session lifecycle
    - [ ] Handle session timeouts
    - [ ] Manage session cleanup

### Milestone 2: Identity Verification (Week 2)
- [ ] **Face Recognition Integration**
  - [ ] Connect to existing face recognition service
    - [ ] Use GhostFaceNets model for embeddings
    - [ ] Implement image preprocessing
    - [ ] Handle base64 image encoding/decoding
  - [ ] Implement face embedding generation
    - [ ] Process captured images
    - [ ] Generate embeddings
    - [ ] Store embeddings in database
  - [ ] Add face matching logic using pgvector
    - [ ] Use cosine similarity for matching
    - [ ] Implement k-nearest neighbors search
    - [ ] Handle multiple face matches
  - [ ] Set confidence thresholds
    - [ ] Define minimum confidence levels
    - [ ] Implement confidence scoring
    - [ ] Add confidence logging

- [ ] **RFID Integration**
  - [ ] Add RFID validation
    - [ ] Validate RFID tag format
    - [ ] Check RFID against employee database
    - [ ] Handle invalid RFID cases
  - [ ] Implement RFID-face matching
    - [ ] Match RFID to employee face embedding
    - [ ] Verify face matches RFID owner
    - [ ] Handle mismatches
  - [ ] Create combined verification logic
    - [ ] Implement verification priority
    - [ ] Handle partial verification
    - [ ] Add verification method tracking

- [ ] **Notification Integration**
  - [ ] Add notification functions to API routes
    - [ ] Implement SMS notifications in session routes
    - [ ] Add ntfy integration to emergency routes
    - [ ] Create notification history table
  - [ ] Add notification triggers for authentication
    - [ ] Failed authentication (3+ attempts) - HIGH priority
    - [ ] Failed biometric verification - MEDIUM priority
  - [ ] Create notification history table
    - [ ] Add notification_history schema
    - [ ] Implement notification logging
    - [ ] Add notification retrieval endpoints

### Milestone 3: Access Control (Week 3)
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

### Milestone 4: Manual Review System (Week 4)
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
- Sample face images
- Test RFID tags
- Session test cases
- Performance test scenarios

### Test Coverage Requirements
- Unit tests: 80% coverage
- Integration tests: 70% coverage
- Performance tests: All critical paths
- Security tests: All security features

### Continuous Integration
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest --cov=api --cov=face_recognition tests/
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

# Add to environment variables
ENABLE_NOTIFICATIONS=true
NOTIFICATION_PHONE_NUMBERS=+1555123456,+1555234567
NTFY_TOPIC=campus-security
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+15551234567

### Milestone 5: Documentation (Week 5)
- [ ] **API Documentation**
  - [ ] Create OpenAPI/Swagger documentation
    - [ ] Document all endpoints
    - [ ] Add request/response examples
    - [ ] Include error responses
  - [ ] Add endpoint usage examples
    - [ ] Session processing examples
    - [ ] Face recognition examples
    - [ ] Notification examples
  - [ ] Document configuration options
    - [ ] Environment variables
    - [ ] Database settings
    - [ ] Service URLs

- [ ] **Setup Documentation**
  - [ ] Create installation guide
    - [ ] Local development setup
    - [ ] Docker setup
    - [ ] Database setup
  - [ ] Add service configuration guide
    - [ ] Face recognition service setup
    - [ ] Database setup
    - [ ] Notification setup
  - [ ] Include troubleshooting guide
    - [ ] Common issues
    - [ ] Error messages
    - [ ] Debug tips

- [ ] **User Documentation**
  - [ ] Create admin guide
    - [ ] Manual review process
    - [ ] Notification management
    - [ ] System monitoring
  - [ ] Add security guide
    - [ ] Access control
    - [ ] Emergency procedures
    - [ ] Security best practices
  - [ ] Include maintenance guide
    - [ ] Backup procedures
    - [ ] Update procedures
    - [ ] Monitoring procedures
