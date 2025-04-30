# Refactoring Plan: CSES Codebase

This document outlines the plan to refactor the CSES codebase for improved organization, maintainability, and clarity.

## Goals

1.  **Standardized Folder Structure:** Create a clear, logical hierarchy for services, hardware code, documentation, and configuration.
2.  **Modular Code:** Refactor monolithic components, especially within the API service, into smaller, focused modules.
3.  **Code Clarity:** Remove unnecessary or AI-generated comments.
4.  **Comprehensive Documentation:** Establish a structured documentation system within the `docs/` folder and create a professional root `README.md`.
5.  **Clear Separation:** Distinguish between locally built services, external services, configuration, and legacy components.

## Target Folder Structure

```
cses/                           # Root directory (formerly Senior Capstone)
├── services/                   # Service-related code and config
│   ├── api/                   # Flask API service (The only service we build)
│   │   ├── src/               # Python source code
│   │   │   ├── core/          # Core app setup (config, exceptions)
│   │   │   ├── models/       # SQLAlchemy models
│   │   │   ├── services/     # Business logic layer
│   │   │   ├── routes/       # API endpoints (Flask Blueprints)
│   │   │   ├── utils/        # Shared utilities
│   │   │   └── app.py        # Application factory (create_app)
│   │   ├── tests/            # Unit and integration tests for the API
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py
│   │   ├── static/           # Static assets (CSS, JS, images)
│   │   ├── templates/        # Jinja2 templates
│   │   ├── Dockerfile        # Builds the API service container
│   │   └── requirements.txt  # Python dependencies
│   ├── database/             # Database setup scripts (PostgreSQL + pgvector)
│   │   ├── init/           # Initialization scripts
│   │   │   ├── init.sql   # Main schema DDL
│   │   │   └── sample_data.sql # Sample data for development
│   │   └── README.md      # Explains DB setup and structure
│   └── mqtt_broker/         # Configuration for local Mosquitto (Legacy)
│       ├── config/         # Mosquitto config files
│       │   └── mosquitto.conf
│       └── README.md      # Explains legacy status (for local dev only)
├── hardware/                  # Embedded systems code (PlatformIO projects)
│   ├── esp32-cam/            # ESP32-CAM code (formerly ESP32-WROVER)
│   │   ├── src/
│   │   ├── lib/
│   │   ├── include/
│   │   ├── test/
│   │   ├── docs/             # Specific docs for ESP32-CAM
│   │   └── platformio.ini
│   ├── controller/           # Arduino Mega code (formerly ArduinoMega)
│   │   ├── src/
│   │   ├── lib/
│   │   ├── include/
│   │   ├── test/
│   │   ├── docs/             # Specific docs for Controller
│   │   └── platformio.ini
│   └── servo/                # Arduino Uno code (formerly ServoArduinoUno)
│       ├── src/
│       ├── lib/
│       ├── include/
│       ├── test/
│       ├── docs/             # Specific docs for Servo
│       └── platformio.ini
├── docs/                     # Project-level documentation
│   ├── api/                 # Auto-generated or manual API docs
│   │   ├── endpoints.md
│   │   ├── authentication.md
│   │   └── data-models.md
│   ├── hardware/           # Overview docs for hardware components
│   │   ├── esp32-cam.md
│   │   ├── controller.md
│   │   └── servo.md
│   ├── deployment/        # Deployment guides
│   │   ├── local-setup.md
│   │   └── production.md    # Details on fly.io deployment
│   ├── architecture/       # System architecture diagrams and explanations
│   │   ├── system-overview.md # High-level diagram and description
│   │   └── data-flow.md     # Sequence diagrams for key flows
│   └── wireframes/       # Existing UI wireframes
├── scripts/               # Utility scripts (e.g., deployment, data generation)
├── tests/                # End-to-end / System-level tests (if any)
├── .gitignore           # Standard git ignore rules
├── docker-compose.yml   # Defines services for local development
└── README.md           # Professional project overview (similar to Voxii example)
```

*Note:* External services like DeepFace are managed via `docker-compose.yml` and don't require dedicated folders in this structure as we are just pulling pre-built images.

## Refactoring Tasks (Step-by-Step)

**Phase 1: Top-Level Structure & Configuration**

- [X] **Backup:** Ensure the current project state is committed to version control.
- [X] **Create Root Directories:** Create `services/` and `hardware/` in the project root.
- [X] **Move Services:**
    - [X] Move the existing `api/` directory into `services/`.
    - [X] Move the existing `database/` directory into `services/`.
    - [X] Move the existing `mqtt_broker/` directory into `services/`.
- [X] **Move Hardware:**
    - [X] Move `ArduinoMega/` into `hardware/` and rename it to `controller/`.
    - [X] Move `ESP32-WROVER/` into `hardware/` and rename it to `esp32-cam/`.
    - [X] Move `ServoArduinoUno/` into `hardware/` and rename it to `servo/`.
- [X] **Update Docker Compose:**
    - [X] Edit `docker-compose.yml`.
    - [X] Update the `build.context` for the `api` service to `./services/api`.
    - [X] Update all volume paths referencing `./api/`, `./database/`, `./mqtt_broker/` to use the new `./services/` prefix (e.g., `./services/api/certs:/app/certs`, `./services/database/init.sql:...`).
- [X] **Test Docker Compose:** Run `docker compose up --build -d` to verify the services start correctly with the new paths. Address any path errors.

**Phase 2: API Service Internal Refactoring**

- [X] **Create `src/`:** Inside `services/api/`, create a `src/` directory.
- [X] **Move API Source Code:** Move the following from `services/api/` into `services/api/src/`:
    - [X] `app.py`
    - [X] `config.py`
    - [X] `models/` directory
    - [X] `routes/` directory
    - [X] `services/` directory (the one containing business logic)
    - [X] `utils/` directory
- [X] **Update API Dockerfile:** Modify `services/api/Dockerfile` to work with the `src/` layout.
    - [X] Change `WORKDIR /app` if necessary.
    - [X] Update `COPY` commands (e.g., `COPY src/requirements.txt .`, `COPY src/ /app`). Adjust based on your current Dockerfile.
    - [X] Ensure the `CMD` or `ENTRYPOINT` correctly points to the application inside `src/` (e.g., `gunicorn "app:create_app()"` might become `gunicorn "src.app:create_app()"`, depending on PYTHONPATH setup).
- [ ] **Modularize API Code:**
    - [ ] Organize files within `services/api/src/` into the target subdirectories (`core`, `models`, `services`, `routes`, `utils`). Create `__init__.py` files in each new Python package directory.
    - [ ] Refactor `app.py` to use an application factory pattern (`create_app()`).
    - [ ] Update all Python `import` statements within `services/api/src/` to use relative imports (e.g., `from .models import User` or `from ..services import auth_service`).
- [ ] **Move API Tests:** Move the existing `tests/` directory into `services/api/`. Update test runner configurations or imports if needed to find tests and source code correctly.
- [ ] **Test API:** Run `docker compose build api` and `docker compose up api`. Execute API tests (e.g., `pytest services/api/tests`). Fix import errors and runtime issues.

**Phase 3: Organizing Other Services & Hardware**

- [ ] **Organize Database:**
    - [ ] Inside `services/database/`, create an `init/` directory.
    - [ ] Move `init.sql` and `sample_data.sql` into `services/database/init/`.
    - [ ] Create `services/database/README.md` explaining its contents and purpose (schema initialization, sample data).
- [ ] **Organize MQTT Broker:**
    - [ ] Inside `services/mqtt_broker/`, create a `config/` directory.
    - [ ] Move `mosquitto.conf` into `services/mqtt_broker/config/`.
    - [ ] Create `services/mqtt_broker/README.md` clearly stating its legacy status and use only for local development.
- [ ] **Standardize Hardware:** For each directory in `hardware/` (`esp32-cam`, `controller`, `servo`):
    - [ ] Verify the standard PlatformIO structure (`src/`, `lib/`, `include/`, `test/`, `platformio.ini`). Create missing directories if needed.
    - [ ] Create a `docs/` subdirectory within each hardware project folder.

**Phase 4: Documentation & Cleanup**

- [ ] **Create Root README:** Draft the main `README.md` in the project root, following a professional structure (like the Voxii example), covering features, architecture, setup, development, etc.
- [ ] **Populate `docs/`:**
    - [ ] Create the necessary subdirectories (`api`, `hardware`, `deployment`, `architecture`) within the main `docs/` folder.
    - [ ] Write initial markdown files for each area (e.g., `docs/architecture/system-overview.md`, `docs/deployment/local-setup.md`).
    - [ ] Add specific `.md` files within each `hardware/*/docs/` folder detailing that component.
- [ ] **Remove AI Comments:** Systematically review `.py`, `.cpp`, `.h` files and remove comments that are redundant, overly verbose, or clearly AI-generated placeholders. Focus on comments explaining *why*, not *what*.
- [ ] **Modularize Code (Further Review):** Revisit key files (especially in the API) identified as potentially monolithic and break them into smaller, more manageable functions or classes if not already addressed during the API refactor.
- [ ] **Final Test:** Run all tests (API tests, hardware builds/tests if available, manual system tests) to ensure everything functions as expected.
