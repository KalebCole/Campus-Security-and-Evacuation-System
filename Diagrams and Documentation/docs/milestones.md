# Campus Security and Evacuation System - Milestone Roadmap

This document outlines the sequential development milestones for the Campus Security and Evacuation System project. Each milestone builds incrementally toward the complete system, with early milestones focused on quick, demonstrable results.

## Milestone 1: Face Recognition Modernization & MQTT Integration
**Goal:** Replace TensorFlow with ESP-WHO and MobileFaceNet, implement MQTT communication for real-time messaging.

### Tasks
- [x] Set up ESP-WHO development environment for ESP32-CAM
- [x] Implement face detection on ESP32-CAM using ESP-WHO framework
- [x] Create image preprocessing pipeline (cropping, resizing to 112x112) - **Note: 112x112 is specifically required for MobileFaceNet's input dimensions**
- [x] Implement MQTT client on ESP32-CAM for sending face images
- [X] Set up local MQTT broker (Mosquitto) for development
- [x] Replace server TensorFlow model with lightweight GhostFaceNets
- [x] Implement server-side MQTT subscription for receiving face images
- [x] Create embedding generation pipeline
- [ ] Create pgvector querying pipeline
- [x] Remove legacy TensorFlow dependencies from server
- [ ] Update Arduino RFID client to use MQTT instead of HTTP
- [x] Define comprehensive MQTT topic structure for device communication
- [ ] Fix the Arduino Uno R4 Client to use MQTT instead of HTTP
- [x] Add state machine for better error handling and recovery to ESP32-CAM
- [x] Implement retry mechanisms for MQTT connections on ESP32-CAM
- [x] Add system status checks before sending face data on ESP32-CAM
- [x] Include device authentication with the server on ESP32-CAM
- [x] Add LED indicators for different states on ESP32-CAM
- [ ] Add MQTT support for real-time status updates on Arduino Uno R4
- [x] Implement better error handling for network issues on Arduino Uno R4
- [x] Add system health monitoring on Arduino Uno R4
- [x] Add support for emergency stop functionality on Arduino Uno R4
- [ ] Implement TLS/SSL for both devices
- [x] Add device authentication for both devices
- [ ] Implement message encryption for both devices
- [ ] Add secure storage for credentials on both devices
- [ ] Implement secure boot for both devices

### Next Steps (Priority Order)
1. **Complete Arduino MQTT Integration**
   - Update Arduino Uno R4 client to use MQTT
   - Implement real-time status updates
   - Test end-to-end communication

2. **Security Enhancements**
   - Implement TLS/SSL for secure communication
   - Add message encryption
   - Set up secure credential storage
   - Implement secure boot

3. **Testing and Documentation**
   - Create comprehensive test suite
   - Document API endpoints
   - Add security documentation
   - Create deployment guide

### Deliverables
- ESP32-CAM firmware with face detection and MQTT publishing
- Local Mosquitto MQTT broker configuration
- Server with MobileFaceNet model for embedding generation
- Working MQTT-based communication between all components
- Significantly reduced server dependencies (no 553MB TensorFlow model)
- Documentation of ESP-WHO integration and MQTT message formats

### Potential Challenges
- **Challenge:** ESP32-CAM memory constraints for detection algorithms
  - **Mitigation:** Optimize code for embedded environment, reduce image resolution when needed
- **Challenge:** MQTT reliability for image transfer
  - **Mitigation:** Implement proper QoS levels and chunking for larger images
- **Challenge:** Maintaining compatibility with existing verification flow
  - **Mitigation:** Create adapter layer to ensure backward compatibility during transition

### Implementation Plan

#### 1. ESP-WHO Setup for ESP32-CAM
- Download ESP-IDF and ESP-WHO framework repositories from GitHub
- Set up development environment with required toolchain (ESP-IDF v4.4+)
- Install dependencies for ESP-WHO (OpenCV components, esp-camera driver)
- Flash ESP32-CAM with basic ESP-WHO example to test functionality

#### 2. MQTT Broker Setup
- Create mqtt directory with Mosquitto configuration
- Download and set up Mosquitto Docker image locally
- Configure allowed connections and ports (1883 for MQTT, 9001 for WebSockets)
- Test broker with simple MQTT client tools to verify functionality

#### 3. ESP32-CAM Face Detection Implementation
- Modify ESP-WHO example code to use face detection model
- Configure camera settings for optimal face capture (resolution, exposure)
- Implement face detection with bounded box extraction
- Add logic to crop detected faces and prepare for transmission

#### 4. MQTT Client on ESP32-CAM
- Add PubSubClient library to ESP32-CAM project
- Configure Wi-Fi and MQTT connection parameters
- Implement reconnection logic and status monitoring
- Create functions to publish detected face images to proper MQTT topics

#### 5. Server-Side MQTT Integration
- Add Eclipse Paho MQTT client library to server requirements
- Create MQTT subscription handler for incoming face images
- Set up callback functions for different message types
- Modify session management to handle MQTT-based input

#### 6. MobileFaceNet Integration
- Replace TensorFlow model with MobileFaceNet (128-dimensional embeddings)
- Create preprocessing pipeline for 112x112 image input
- Implement embedding generation using MobileFaceNet
- Update verification logic to use cosine similarity with embeddings

#### 7. Arduino MQTT Conversion
- Modify Arduino code to use MQTT instead of HTTP
- Update message structure for RFID transmission
- Implement state management for MQTT connection
- Add QoS settings for reliable message delivery

#### 8. Testing and Verification
- Create test harness for end-to-end verification flow
- Test face detection accuracy with various conditions
- Verify MQTT message delivery reliability
- Measure system latency compared to HTTP-based approach

#### 9. Documentation Updates
- Document MQTT topic structure and message formats
- Create wiring and setup instructions for ESP32-CAM
- Update system architecture diagrams to reflect MQTT flow
- Document MobileFaceNet embedding generation process

#### 10. Fix the Arduino Uno R4 Client to use MQTT instead of HTTP
- Modify the Arduino Uno R4 Client to use MQTT instead of HTTP
- Update the message structure for RFID transmission
- Implement state management for MQTT connection
- Add QoS settings for reliable message delivery


### Testing Strategy

#### Component-Level Testing

##### 1. ESP-WHO Framework
- Run ESP-WHO example apps on ESP32-CAM with known test faces
- Verify face detection works by checking bounding box coordinates
- Test in different lighting conditions and distances
- Output detection results to serial monitor for validation
- Create visual indicators (LED flashes) for real-time detection feedback

##### 2. MQTT Broker
- Use MQTT Explorer or Mosquitto CLI tools to subscribe to test topics
- Run broker diagnostics to verify proper configuration
- Test connection limits and message throughput
- Verify topic security and access controls
- Test connection persistence through network interruptions

##### 3. ESP32-CAM MQTT Client
- Create simple test harness to verify message publishing
- Monitor message publishing success rate and timing
- Test reconnection behavior when broker connection is lost
- Verify QoS settings are working correctly
- Test with various payload sizes to determine optimal image format

##### 4. Server MobileFaceNet
- Create benchmark test suite with known face pairs (same/different)
- Compare accuracy metrics against existing TensorFlow implementation
- Test processing speed for different input sizes
- Validate embedding vector dimensions (should be 128)
- Test with challenging cases (occlusion, poor lighting, angles)

##### 5. Arduino MQTT Conversion
- Create echo tests to verify send/receive functionality
- Test state transitions in MQTT connection handling
- Verify RFID data is correctly formatted in MQTT messages
- Test reconnection behavior

#### Integration Testing

##### 1. Camera + MQTT
- Capture face, send over MQTT, verify message received
- Test different image formats (JPEG compression levels)
- Measure end-to-end latency
- Test with concurrent connections

##### 2. Server + MQTT
- Verify server correctly subscribes to face image topics
- Test that incoming messages trigger proper processing
- Verify session management works with MQTT-based flow

##### 3. Arduino + MQTT
- Verify RFID messages flow correctly through MQTT
- Test coordination between RFID and face verification

#### System Testing

##### 1. End-to-End Test Rig
- Set up physical test environment with ESP32-CAM and Arduino RFID
- Create test scenarios with known users in database
- Time full verification process from face capture to access decision
- Test false positive/negative scenarios

##### 2. Load Testing
- Simulate multiple concurrent verification requests
- Measure system performance under load
- Identify bottlenecks

##### 3. Failure Testing
- Test behavior when components fail (broker offline, etc.)
- Verify graceful degradation and recovery

#### Test Tools
- MQTT Explorer - For monitoring broker messages
- Wireshark - For analyzing MQTT network traffic
- ESP32 Serial Monitor - For debug output
- Custom Python test scripts - For simulating devices and validation
- MQTT.fx - For manual testing of MQTT flows

## Milestone 2: Containerization, Database Migration & Cloud Deployment
**Goal:** Containerize all backend components, implement Supabase with pgvector, and prepare for cloud deployment on fly.io.

### Tasks
- [ ] Set up Supabase project with pgvector extension
- [ ] Create employee database schema with embedding vector field
- [ ] Migrate existing mock data to Supabase
- [ ] Create optimized Dockerfile for server components
- [ ] Containerize MQTT broker with proper configuration
- [ ] Create Docker Compose orchestration for all backend services
- [ ] Implement volume mapping for persistent storage
- [ ] Set up environment variable management for container configuration
- [ ] Create development and production container configurations
- [ ] Automate container build process
- [ ] Set up MQTT broker on fly.io with proper TLS security
- [ ] Configure fly.io volumes for persistent storage
- [ ] Deploy containerized server application to fly.io
- [ ] Configure environment variables and secrets
- [ ] Update clients to connect to cloud MQTT broker
- [ ] Implement proper error handling for cloud connectivity
- [ ] Create deployment documentation and operational guides

### Deliverables
- Complete Docker Compose setup for all backend services
- Containerized server API with MobileFaceNet integration
- Containerized MQTT broker with proper security
- Functional Supabase database with pgvector support
- Local development container environment
- Production-ready container configurations
- Server application deployed on fly.io
- Configuration documentation for containers and cloud services
- Updated client configurations for cloud connectivity

### Potential Challenges
- **Challenge:** Container optimization for performance and size
  - **Mitigation:** Use multi-stage builds and alpine-based images
- **Challenge:** Secure MQTT broker configuration in containers
  - **Mitigation:** Implement proper certificate management and volume mapping
- **Challenge:** Managing secrets and configuration across environments
  - **Mitigation:** Use environment variables and Docker secrets
- **Challenge:** Network reliability for ESP32-CAM to cloud communication
  - **Mitigation:** Add robust reconnection logic and message buffering

## Milestone 3: Database API & Security Enhancement
**Goal:** Create a comprehensive API for database operations and enhance system security.

### Tasks
- [ ] Implement repository pattern for Supabase data access
- [ ] Create API endpoints for employee management (CRUD)
- [ ] Add access log recording and querying functionality
- [ ] Implement notification storage and retrieval
- [ ] Add user authentication for API access
- [ ] Implement rate limiting and request validation
- [ ] Create API documentation with Swagger/OpenAPI
- [ ] Add comprehensive error handling and logging
- [ ] Implement session management for security operations
- [ ] Create data migration tools for schema evolution

### Deliverables
- Comprehensive API for all database operations
- Security enhancements for API access
- API documentation and usage examples
- Data migration utilities
- Testing suite for API functionality

### Potential Challenges
- **Challenge:** Maintaining API performance with increased functionality
  - **Mitigation:** Implement caching and database query optimization
- **Challenge:** Securing API endpoints properly
  - **Mitigation:** Use industry-standard authentication and follow OWASP guidelines

## Milestone 4: Monitoring Frontend
**Goal:** Create a React dashboard for system monitoring and employee management.

### Tasks
- [ ] Set up React project structure with TypeScript
- [ ] Create login page for security personnel
- [ ] Implement real-time notifications using ntfy
- [ ] Create access log visualization component
- [ ] Add employee management interface (CRUD)
- [ ] Implement face embedding enrollment for new employees
- [ ] Create system status monitoring dashboard
- [ ] Add responsive layout for desktop/mobile
- [ ] Implement search and filtering functionality
- [ ] Connect frontend directly to Supabase for data operations

### Deliverables
- Functional React dashboard
- Real-time notification display
- Employee management interface with face enrollment
- Access log visualization and filtering
- Responsive design for various device sizes

### Potential Challenges
- **Challenge:** Real-time updates without performance issues
  - **Mitigation:** Use efficient rendering techniques, pagination, and virtualization
- **Challenge:** Face embedding enrollment user experience
  - **Mitigation:** Create intuitive UI with proper guidance and validation

## Milestone 5: CI/CD Pipeline & Testing
**Goal:** Set up continuous integration and delivery pipeline with automated testing.

### Tasks
- [ ] Set up GitHub Actions workflow for CI/CD
- [ ] Implement automated testing for server components
- [ ] Create end-to-end testing for critical flows
- [ ] Add performance testing for database operations
- [ ] Implement code quality checks (linting, formatting)
- [ ] Set up automated deployment to fly.io
- [ ] Configure environment-specific builds (dev, staging, prod)
- [ ] Create testing documentation
- [ ] Implement code coverage reporting
- [ ] Add security scanning for dependencies

### Deliverables
- GitHub Actions workflow configuration
- Automated test suite for all components
- CI/CD pipeline with quality checks
- Automated deployment process
- Testing documentation and guidelines

### Potential Challenges
- **Challenge:** Testing embedded device code
  - **Mitigation:** Create simulators and mocks for hardware components
- **Challenge:** Ensuring test environment isolation
  - **Mitigation:** Use dedicated test databases and resources

## Milestone 6: Analytics & Advanced Monitoring
**Goal:** Enhance the system with analytics capabilities and advanced monitoring.

### Tasks
- [ ] Set up Grafana instance on fly.io
- [ ] Create dashboards for access patterns
- [ ] Implement anomaly detection for suspicious activities
- [ ] Add system health monitoring
- [ ] Create custom alerts based on metrics
- [ ] Implement data visualization for security insights
- [ ] Add PDF report generation for audits
- [ ] Create user activity heatmaps and trends
- [ ] Set up log aggregation and analysis
- [ ] Implement performance metrics collection

### Deliverables
- Grafana dashboards for system monitoring
- Anomaly detection for security events
- Custom alert configurations
- Audit report generation
- Performance monitoring solution

### Potential Challenges
- **Challenge:** Collecting appropriate metrics without performance impact
  - **Mitigation:** Use efficient metric collection, sampling for high-volume data
- **Challenge:** Creating meaningful visualizations
  - **Mitigation:** Start with essential metrics, refine based on security personnel feedback

## Milestone 7: System Integration & Scaling
**Goal:** Ensure all components work together seamlessly and implement scaling capabilities.

### Tasks
- [ ] Conduct end-to-end testing of complete system flow
- [ ] Implement load testing with simulated traffic
- [ ] Configure auto-scaling policies for cloud components
- [ ] Create disaster recovery procedures
- [ ] Optimize system performance based on testing results
- [ ] Implement multi-region deployment options
- [ ] Create comprehensive documentation for operations
- [ ] Set up monitoring for scaling events
- [ ] Implement database read replicas for scaling
- [ ] Create user training materials

### Deliverables
- Fully integrated system with scaling capabilities
- Load testing results and performance metrics
- Disaster recovery documentation
- Operational guides and training materials
- Multi-region deployment configuration

### Potential Challenges
- **Challenge:** Ensuring consistent performance during scaling events
  - **Mitigation:** Implement proper connection pooling and graceful scaling procedures
- **Challenge:** Managing distributed system complexity
  - **Mitigation:** Create comprehensive monitoring and centralized logging 


## Milestone X: Model Training and Fine-tuning
**Goal:** Enhance face recognition accuracy by training the model on campus-specific data.

### Tasks
- [ ] Collect and curate campus-specific face dataset
- [ ] Implement data augmentation pipeline
- [ ] Set up model training infrastructure
- [ ] Configure training parameters (loss function, optimizer, metrics)
- [ ] Implement model evaluation and validation
- [ ] Create model versioning system
- [ ] Document training process and results
- [ ] Implement A/B testing for model performance
- [ ] Set up continuous training pipeline

### Deliverables
- Curated dataset of campus faces
- Trained and fine-tuned face recognition model
- Training pipeline documentation
- Model evaluation metrics and benchmarks
- Version control system for models
- A/B testing framework

### Potential Challenges
- **Challenge:** Data privacy and collection
  - **Mitigation:** Implement strict data handling policies, obtain proper consent
- **Challenge:** Model overfitting to campus data
  - **Mitigation:** Use transfer learning, maintain generalizability
- **Challenge:** Training infrastructure requirements
  - **Mitigation:** Use cloud resources, implement efficient training pipeline

### Implementation Plan

#### 1. Data Collection and Preparation
- Define data collection protocol
- Implement data anonymization
- Create data validation pipeline
- Set up data storage and versioning

#### 2. Training Infrastructure
- Set up GPU-enabled training environment
- Implement data loading pipeline
- Configure model compilation for training
- Set up training monitoring

#### 3. Model Training
- Implement transfer learning approach
- Configure training parameters
- Set up validation pipeline
- Implement early stopping

#### 4. Evaluation and Deployment
- Create evaluation metrics
- Implement A/B testing
- Set up model versioning
- Create deployment pipeline

Other Tasks:
- [ ] Improve the session management for the ESP32-CAM and the Arduino Uno R4 so that there can be more than 1 session on the serverside
- [ ] Implement a way to have a timer for the sessions so that they can be deleted after a certain amount of time
- [ ] Implement locking and unlocking mechanisms for the door
- [ ] Create a Script to automate the Texas Instruments writing of the signals to the txt file that go directly to the Mega or to my server

