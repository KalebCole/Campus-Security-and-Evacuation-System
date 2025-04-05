# Campus Security and Evacuation System - Milestone Roadmap

This document outlines the sequential development milestones for the Campus Security and Evacuation System project. Each milestone builds incrementally toward the complete system, with early milestones focused on quick, demonstrable results.

## Milestone 1: Face Recognition Modernization & MQTT Integration
**Goal:** Replace TensorFlow with ESP-WHO and MobileFaceNet, implement MQTT communication for real-time messaging.

### Tasks
- [ ] Set up ESP-WHO development environment for ESP32-CAM
- [ ] Implement face detection on ESP32-CAM using ESP-WHO framework
- [ ] Create image preprocessing pipeline (cropping, resizing to 112x112) - **Note: 112x112 is specifically required for MobileFaceNet's input dimensions**
- [ ] Implement MQTT client on ESP32-CAM for sending face images
- [ ] Set up local MQTT broker (Mosquitto) for development
- [ ] Replace server TensorFlow model with lightweight MobileFaceNet
- [ ] Implement server-side MQTT subscription for receiving face images
- [ ] Create embedding generation and pgvector querying pipeline
- [ ] Remove legacy TensorFlow dependencies from server
- [ ] Update Arduino RFID client to use MQTT instead of HTTP
- [ ] Define comprehensive MQTT topic structure for device communication

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