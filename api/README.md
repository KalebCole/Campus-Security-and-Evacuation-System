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
        - Extract `session_id`, `image_data` (base64), `rfid_detected`, `face_detected`, `rfid_tag` (if present), etc.
        - **(Verification Flow Start)**
        - If `image_data` exists: Call `face_client.get_embedding(image_data)` -> `new_embedding`.
        - If `rfid_detected` and `rfid_tag` exists: Call `database_service.get_employee_by_rfid(rfid_tag)` -> `employee_record`.
        - **(Verification Logic)**
        - If `employee_record` and `new_embedding` and `employee_record.face_embedding` exist (and `face_detected` is true):
            - Call `face_client.verify_embeddings(new_embedding, employee_record.face_embedding)` -> `verification_result`.
            - Determine `access_granted` based on `verification_result['is_match']` and `verification_result['confidence']` (check against a threshold).
            - Set `verification_method` to 'RFID+FACE'.
        - Else if `new_embedding` exists (e.g., `face_detected` is true, but no valid RFID):
            - *Optional: Implement face-only search:* Call `database_service.find_similar_embeddings(new_embedding)` -> `matches`.
            - Set `access_granted = False`, `verification_method` = 'FACE_ONLY_PENDING_REVIEW'.
        - Else if `employee_record` exists (e.g., `rfid_detected` is true, but `face_detected` is false, even though `image_data` was sent):
            - Set `access_granted = False` (requires manual review).
            - Set `verification_method` = 'RFID_ONLY_PENDING_REVIEW'.
        - Else (no RFID match, no face detected, or other error):
             - Set `access_granted = False`, `verification_method` = 'ERROR/INCOMPLETE'.
        - **(Logging & Updates)**
        - Call `database_service.save_verification_image(...)` with image data, session ID, results.
        - Call `database_service.log_access_attempt(...)` with session ID, employee ID, method, granted status, confidence, and appropriate `review_status`.
        - Update `SessionRecord` in DB via `database_service.update_session(...)` (if needed).
        - If `access_granted`: Publish unlock command to `campus/security/unlock`.
- [X] **Handle Emergency Messages (`campus/security/emergency`)**
    - In `on_message`, if topic is `campus/security/emergency`:
        - Parse JSON payload.
        - Log the emergency event (source, timestamp).
        - Publish unlock command to `campus/security/unlock`.
- [X] **Publish Unlock Messages (`campus/security/unlock`)**
    - [X] Define standard JSON payload (e.g., `{\"command\": \"UNLOCK\", \"session_id\": \"...\"}`).
    - [X] Implement helper method in MQTT service to publish this message.
    - [X] Call publish method when access granted or emergency occurs.
- [X] **Integrate MQTT Service into App Startup**
    - [X] Instantiate `MQTTService` in `app.py` after other services.
    - [X] Call `mqtt_service.connect()` to start listening.
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
  - [X] Handle base64 image encoding/decoding
  - [X] Add face matching logic using pgvector
  - [X] Set confidence thresholds

- [X] **RFID Integration**
  - [X] Add RFID
  - [X] Implement RFID-face matching
  - [X] Verify face matches RFID owner
  - [X] Handle mismatches
  - [X] Create combined verification logic

- [X] **Notification Integration**
  - [X] **Setup Notification Service (`services/notification_service.py`)**
    - [X] Create service class incorporating logic from diagrams/previous code.
    - [X] Initialize Twilio client using configured credentials.
    - [X] Implement sending to ntfy topic (`ntfy.sh/cses-access-alerts` or similar) via `requests`.
    - [X] Define rules for channel selection based on severity (e.g., SMS, ntfy).
  - [X] **Define Notification Model (`models/notification.py`)**
    - [X] Create `Notification` dataclass based on class diagram.
    - [X] Define `NotificationType` enum based on class diagram (`RFID_NOT_FOUND`, `FACE_NOT_RECOGNIZED`, `ACCESS_GRANTED`, etc.).
    - [X] Define `SeverityLevel` enum based on class diagram (`INFO`, `WARNING`, `CRITICAL`).
  - [X] **Configure Notification Settings (`config.py`, `.env.development`)**
    - [X] Add `TWILIO_*` variables, `NOTIFICATION_PHONE_NUMBERS`, `NTFY_TOPIC`, `ENABLE_NOTIFICATIONS`.
  - [X] **Implement Notification Database History**
    - [X] Define `notification_history` table schema in `database/init.sql`.
    - [X] Create `NotificationHistory` SQLAlchemy model.
    - [X] Add `save_notification_to_history()` method to `DatabaseService`.
    - [X] Ensure `MQTTService` calls `database_service.save_notification_to_history()` after triggering a notification.
  - [X] **Integrate Notification Triggers (`services/mqtt_service.py`)**
    - [X] Inject `NotificationService` into `MQTTService`.
    - [X] Trigger `ACCESS_GRANTED` notification (Severity: `INFO`) on success.
    - [X] Trigger `FACE_NOT_RECOGNIZED` notification (Severity: `WARNING`/`CRITICAL`) on face verification failure.
    - [X] Trigger `RFID_NOT_FOUND` notification (Severity: `WARNING`) when detected RFID tag is unknown.
    - [X] Instantiate `Notification` model with relevant context at trigger points.
    - [X] Call `notification_service.send_notification()`.
  - [X] **Update Dependencies (`requirements.txt`)**
    - [X] Add `twilio` and `requests`.

### Milestone 4: Access Control (Week 4)
- [X] **Define Verification Policy:** RFID+Face grants access. RFID-only (image sent but face not detected) or Face-only (no valid RFID) require Manual Review. Emergency grants access.
- [X] **Implement RFID-Only Flagging for Manual Review**
    - [X] In `mqtt_service` (`elif employee_record:` path, check also that `face_detected` is false):
        - Ensure `access_granted = False`.
        - Set `verification_method` to `"RFID_ONLY_PENDING_REVIEW"`.
        - Trigger notification (`MANUAL_REVIEW_REQUIRED`, Severity `INFO`/`WARNING`).
        - Ensure `log_access_attempt` sets `review_status` to `pending`.
- [X] **Implement Face-Only Flagging for Manual Review**
    - [X] In `mqtt_service` (`elif new_embedding:` path, likely no `employee_record`):
        - Ensure `access_granted = False`.
        - Call `db_service.find_similar_embeddings` to get potential matches for review context.
        - Set `verification_method` to `"FACE_ONLY_PENDING_REVIEW"`.
        - Trigger notification (`MANUAL_REVIEW_REQUIRED`, Severity `INFO`/`WARNING`), including similarity results in `additional_data`.
        - Ensure `log_access_attempt` sets `review_status` to `pending`.
- [X] **RFID+Face Combined Verification**
- [X] **Emergency Override Handling**
    - [X] Enhance logging in `_handle_emergency_message`.
    - [X] Implement specific `NotificationType.EMERGENCY_OVERRIDE`.
    - [ ] (Optional) Define "Emergency Mode" state if needed.

- [X] **Access Logging**
  - [X] Create access log entries (`db_service.log_access_attempt` called).
  - [X] Add verification method tracking (`verification_method` logged).
  - [X] Implement confidence score logging (`verification_confidence` logged).
  - [X] Add image storage for verification (`db_service.save_verification_image` called).

- [X] **Access Control Notifications**
  - [X] Implement `NotificationType.EMERGENCY_OVERRIDE` trigger.
  - [X] Implement `NotificationType.MANUAL_REVIEW_REQUIRED` trigger for RFID-only/Face-only.
  - [ ] Refine `SYSTEM_ERROR` notifications for more specific causes where possible.
  - [ ] (Optional) Define/Implement trigger for `Unauthorized access attempt`.
  - [ ] (Out of Scope?) `Door left open warning`.

### Milestone 5: Manual Review System & Enhancements

**Goal:** Implement and enhance the web-based interface for administrators to review flagged access attempts, manage access decisions, and view access history.

**Task 1: Minimal Database Schema & Model Update** (Completed)
- **Goal:** Prepare the database to store the review decision status and ensure session uniqueness.
- **Subtasks:**
    - [X] Modify `access_logs` table (`database/init.sql`):
        - [X] Add `review_status` column (`VARCHAR(20)` default 'pending').
        - [X] Add `UNIQUE` constraint to `session_id` column.
    - [X] Update SQLAlchemy model for `AccessLog` (`models/access_log.py`) for `review_status`.

**Task 2: Core Backend Routes & Database Logic** (Completed)
- **Goal:** Create the fundamental API endpoints and database interactions for review.
- **Subtasks:**
    - [X] Create `api/routes/admin.py` with Flask Blueprint (`admin_bp`).
    - [X] Implement `DatabaseService` methods: `get_pending_review_sessions`, `get_session_review_details`, `update_review_status`.
    - [X] Implement Flask routes: `GET /pending`, `GET /details/<uuid>`, `POST /approve/<uuid>`, `POST /deny/<uuid>`.
    - [X] Register `admin_bp` in `app.py`.
    - [X] Update `sample_data.sql` for UUIDs and explicit `review_status`.
    - [X] Add specific `IntegrityError` handling in `mqtt_service.py` for duplicate `session_id`.

**Task 3: Basic Frontend Framework** (Completed)
- **Goal:** Set up the HTML templates and basic interaction.
- **Subtasks:**
    - [X] Create `templates/admin` directory and files (`pending_reviews.html`, `review_details.html`).
    - [X] Implement basic table display in `pending_reviews.html`.
    - [X] Implement basic detail display and JS for Approve/Deny buttons in `review_details.html`.
    - [X] Update Flask routes to render these templates.

**Task 4: Enhance Review Logic & UI** (Current Focus)
- **Goal:** Improve backend logic for different scenarios and create distinct UI views for each review type.
- **Subtasks:**
    - [ ] Modify `mqtt_service.py` to skip face embedding if `face_detected` is false.
    - [ ] Modify `mqtt_service.py` to set distinct `verification_method` (e.g., `'FACE_VERIFICATION_FAILED'`) on failed RFID+Face verification if review is desired.
    - [ ] Modify `db_service.log_access_attempt` and `mqtt_service.py` call to auto-approve successful RFID+Face attempts.
    - [ ] Implement conditional rendering in `review_details.html` based on `verification_method`.
    - [ ] **RFID-Only View:** Display employee details, reference photo, captured photo (noting no face detected). Standard Approve/Deny.
    - [ ] **Face-Only View:** Display captured photo, potential match cards. Implement two-step approval (select match -> enable Approve).
    - [ ] **Face Verification Failed View:** Display employee details, reference photo, captured photo, and failed confidence score. Standard Approve/Deny.
    - [ ] Ensure employee `photo_url` is fetched and displayed where needed.

**Task 5: Access Log Viewer** (Next Feature)
- **Goal:** Provide a searchable/filterable view of all access logs.
- **Subtasks:**
    - [ ] Add `DatabaseService` method `get_all_access_logs` with filtering/pagination.
    - [ ] Add Flask route (`/admin/logs`).
    - [ ] Create `admin/access_logs.html` template with table and filters.
    - [ ] Add JS for filtering/searching.

**Task 6 (Future): Advanced Features** (Deferred - formerly Task 4)
- **Goal:** Add auditability, user tracking, reasons, and polish.
- **Subtasks:**
    - [ ] Implement detailed audit logging (`admin_audit_logs` table).
    - [ ] Add `reviewed_by`, `review_timestamp`, `review_reason` columns to `access_logs`.
    - [ ] Implement Authentication & Authorization for admin routes.
    - [ ] Implement Pagination for lists.
    - [ ] Add 'Deny Reason' input.
    - [ ] Create Admin Dashboard summary page.

### Milestone 6: Cleanup and Optimization (Future)

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
