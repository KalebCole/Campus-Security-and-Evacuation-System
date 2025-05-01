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
- [X] **Modularize API Code:**
    - [X] Organize files within `services/api/src/` into the target subdirectories (`core`, `models`, `services`, `routes`, `utils`). Create `__init__.py` files in each new Python package directory.
    - [X] Refactor `app.py` to use an application factory pattern (`create_app()`).
    - [X] Update all Python `import` statements within `services/api/src/` to use relative imports (e.g., `from .models import User` or `from ..services import auth_service`).
- [X] **Move API Tests:** Move the existing `tests/` directory into `services/api/`. Update test runner configurations or imports if needed to find tests and source code correctly.
- [X] **Test API:** Run `docker compose build api` and `docker compose up api`. Execute API tests (e.g., `pytest services/api/tests`). Fix import errors and runtime issues.

**Phase 3: Documentation & Cleanup**

- [X] **Create Root README:** Draft the main `README.md` in the project root, following a professional structure (like the Voxii example), covering features, architecture, setup, development, etc.
- [ ] **Remove AI Comments:** Systematically review `.py`, `.cpp`, `.h` files and remove comments that are redundant, overly verbose, or clearly AI-generated placeholders. Focus on comments explaining *why*, not *what*.
- [ ] **Modularize Code (Further Review):** Revisit key files (especially in the API) identified as potentially monolithic and break them into smaller, more manageable functions or classes if not already addressed during the API refactor.
- [ ] **Final Test:** Run all tests (API tests, hardware builds/tests if available, manual system tests) to ensure everything functions as expected.






## Other tasks

- [ ] Update the tests to use the new folder structure
```
(venv) PS C:\Users\kaleb\Documents\00_College\Senior Capstone\services\api> pytest.exe .\tests\
============================================================== test session starts ==============================================================
platform win32 -- Python 3.13.2, pytest-7.4.0, pluggy-1.5.0
rootdir: C:\Users\kaleb\Documents\00_College\Senior Capstone
configfile: pytest.ini
plugins: anyio-4.9.0, cov-4.1.0, mock-3.14.0
collected 6 items / 4 errors                                                                                                                     

==================================================================== ERRORS =====================================================================
_________________________________ ERROR collecting services/api/tests/integration/test_mqtt_session_handling.py _________________________________ 
ImportError while importing test module 'C:\Users\kaleb\Documents\00_College\Senior Capstone\services\api\tests\integration\test_mqtt_session_handling.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Program Files\Python313\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests\integration\test_mqtt_session_handling.py:15: in <module>
    from models.notification import NotificationType, SeverityLevel
E   ModuleNotFoundError: No module named 'models'
_____________________________________ ERROR collecting services/api/tests/verification/test_auto_approve.py _____________________________________ 
tests\verification\test_auto_approve.py:28: in <module>
    orig = Image.open(IMAGE_PATH)
venv\Lib\site-packages\PIL\Image.py:3505: in open
    fp = builtins.open(filename, "rb")
E   FileNotFoundError: [Errno 2] No such file or directory: '..\\..\\static\\images\\tests\\auto_approve_review.png'

During handling of the above exception, another exception occurred:
venv\Lib\site-packages\_pytest\runner.py:341: in from_call
    result: Optional[TResult] = func()
venv\Lib\site-packages\_pytest\runner.py:372: in <lambda>
    call = CallInfo.from_call(lambda: list(collector.collect()), "collect")
venv\Lib\site-packages\_pytest\python.py:531: in collect
    self._inject_setup_module_fixture()
venv\Lib\site-packages\_pytest\python.py:545: in _inject_setup_module_fixture
    self.obj, ("setUpModule", "setup_module")
venv\Lib\site-packages\_pytest\python.py:310: in obj
    self._obj = obj = self._getobj()
venv\Lib\site-packages\_pytest\python.py:528: in _getobj
    return self._importtestmodule()
venv\Lib\site-packages\_pytest\python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
venv\Lib\site-packages\_pytest\pathlib.py:565: in import_path
    importlib.import_module(module_name)
C:\Program Files\Python313\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1331: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:935: in _load_unlocked
    ???
venv\Lib\site-packages\_pytest\assertion\rewrite.py:178: in exec_module
    exec(co, module.__dict__)
tests\verification\test_auto_approve.py:45: in <module>
    exit(1)
<frozen _sitebuiltins>:26: in __call__
    ???
E   SystemExit: 1
---------------------------------------------------------------- Captured stdout ---------------------------------------------------------------- 
Error: Image file not found at ..\..\static\images\tests\auto_approve_review.png
______________________________________ ERROR collecting services/api/tests/verification/test_face_only.py _______________________________________ 
tests\verification\test_face_only.py:28: in <module>
    orig = Image.open(IMAGE_PATH)
venv\Lib\site-packages\PIL\Image.py:3505: in open
    fp = builtins.open(filename, "rb")
E   FileNotFoundError: [Errno 2] No such file or directory: '..\\..\\static\\images\\employees\\EMP021.jpg'

During handling of the above exception, another exception occurred:
venv\Lib\site-packages\_pytest\runner.py:341: in from_call
    result: Optional[TResult] = func()
venv\Lib\site-packages\_pytest\runner.py:372: in <lambda>
    call = CallInfo.from_call(lambda: list(collector.collect()), "collect")
venv\Lib\site-packages\_pytest\python.py:531: in collect
    self._inject_setup_module_fixture()
venv\Lib\site-packages\_pytest\python.py:545: in _inject_setup_module_fixture
    self.obj, ("setUpModule", "setup_module")
venv\Lib\site-packages\_pytest\python.py:310: in obj
    self._obj = obj = self._getobj()
venv\Lib\site-packages\_pytest\python.py:528: in _getobj
    return self._importtestmodule()
venv\Lib\site-packages\_pytest\python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
venv\Lib\site-packages\_pytest\pathlib.py:565: in import_path
    importlib.import_module(module_name)
C:\Program Files\Python313\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1331: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:935: in _load_unlocked
    ???
venv\Lib\site-packages\_pytest\assertion\rewrite.py:178: in exec_module
    exec(co, module.__dict__)
tests\verification\test_face_only.py:53: in <module>
    exit(1)
<frozen _sitebuiltins>:26: in __call__
    ???
E   SystemExit: 1
---------------------------------------------------------------- Captured stdout ---------------------------------------------------------------- 
Error: Image file not found at ..\..\static\images\employees\EMP021.jpg
______________________________________ ERROR collecting services/api/tests/verification/test_rfid_only.py _______________________________________ 
tests\verification\test_rfid_only.py:28: in <module>
    orig = Image.open(IMAGE_PATH)
venv\Lib\site-packages\PIL\Image.py:3505: in open
    fp = builtins.open(filename, "rb")
E   FileNotFoundError: [Errno 2] No such file or directory: '..\\..\\static\\images\\tests\\rfid_only_review.png'

During handling of the above exception, another exception occurred:
venv\Lib\site-packages\_pytest\runner.py:341: in from_call
    result: Optional[TResult] = func()
venv\Lib\site-packages\_pytest\runner.py:372: in <lambda>
    call = CallInfo.from_call(lambda: list(collector.collect()), "collect")
venv\Lib\site-packages\_pytest\python.py:531: in collect
    self._inject_setup_module_fixture()
venv\Lib\site-packages\_pytest\python.py:545: in _inject_setup_module_fixture
    self.obj, ("setUpModule", "setup_module")
venv\Lib\site-packages\_pytest\python.py:310: in obj
    self._obj = obj = self._getobj()
venv\Lib\site-packages\_pytest\python.py:528: in _getobj
    return self._importtestmodule()
venv\Lib\site-packages\_pytest\python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
venv\Lib\site-packages\_pytest\pathlib.py:565: in import_path
    importlib.import_module(module_name)
C:\Program Files\Python313\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1331: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:935: in _load_unlocked
    ???
venv\Lib\site-packages\_pytest\assertion\rewrite.py:178: in exec_module
    exec(co, module.__dict__)
tests\verification\test_rfid_only.py:53: in <module>
    exit(1)
<frozen _sitebuiltins>:26: in __call__
    ???
E   SystemExit: 1
---------------------------------------------------------------- Captured stdout ---------------------------------------------------------------- 
Error: Image file not found at ..\..\static\images\tests\rfid_only_review.png
=============================================================== warnings summary ================================================================ 
venv\Lib\site-packages\pydantic\_internal\_config.py:323
venv\Lib\site-packages\pydantic\_internal\_config.py:323
  C:\Users\kaleb\Documents\00_College\Senior Capstone\services\api\venv\Lib\site-packages\pydantic\_internal\_config.py:323: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.11/migration/
    warnings.warn(DEPRECATION_MESSAGE, DeprecationWarning)

src\services\database.py:27
  C:\Users\kaleb\Documents\00_College\Senior Capstone\services\api\src\services\database.py:27: MovedIn20Warning: The ``declarative_base()`` function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)  
    Base = declarative_base()

venv\Lib\site-packages\paho\mqtt\client.py:792
  C:\Users\kaleb\Documents\00_College\Senior Capstone\services\api\venv\Lib\site-packages\paho\mqtt\client.py:792: DeprecationWarning: ssl.PROTOCOL_TLS is deprecated
    context = ssl.SSLContext(tls_version)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============================================================ short test summary info ============================================================
ERROR tests\integration\test_mqtt_session_handling.py
ERROR tests\verification\test_auto_approve.py - SystemExit: 1
ERROR tests\verification\test_face_only.py - SystemExit: 1
ERROR tests\verification\test_rfid_only.py - SystemExit: 1
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Interrupted: 4 errors during collection !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 
======================================================== 4 warnings, 4 errors in 12.16s ========================================================= 
(venv) PS C:\Users\kaleb\Documents\00_College\Senior Capstone\services\api> 
```
