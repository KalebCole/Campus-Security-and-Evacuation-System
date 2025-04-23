# Project Milestones - CSES Admin Dashboard (Flask/Jinja Focus)

This document outlines the milestones required to enhance the Flask/Jinja admin dashboard.

**Target State:**
*   Functional admin dashboard using Flask/Jinja templates and Bootstrap styling.
*   Features include Access Log review (Pending, Today, Previous), detailed review actions, Employee CRUD, and Emergency Status display.
*   Focus on core functionality and simplicity due to time constraints.

---
# ADMIN DASHBOARD MILESTONES (Flask/Jinja)

## Milestone 6: Admin Dashboard - Base Layout & Navigation (Flask/Jinja + Bootstrap)

**Goal:** Enhance the base Jinja template and navigation structure using Bootstrap 5.

*   [X] **Template:** Modify `api/templates/admin/base.html`.
    *   [X] Add Bootstrap 5 CSS & JS CDN links in the `<head>` and before `</body>`.
    *   [X] Add Bootstrap Table CSS & JS CDN links.
    *   [X] Implement a persistent side navigation bar section using Bootstrap grid/flex classes.
    *   [X] Add navigation links for "Access Logs" and "Employees".
    *   [X] Ensure the `{% block content %}{% endblock %}` is positioned correctly relative to the sidebar (e.g., using Bootstrap grid layout).
*   [X] **Flask:** Update relevant Flask routes to render templates extending `base.html`.
*   [X] **Pending Count Badge (Option 1 - Server-Side):**
    *   [X] **Flask:** Fetch pending count in route.
    *   [X] **Flask:** Pass `pending_count` to context.
    *   [X] **Template:** In `base.html`, conditionally display a Bootstrap badge (`<span class="badge bg-danger">...</span>`) with `{{ pending_count }}`.

## Milestone 7: Admin Dashboard - Access Logs View (Pending/Today Cards - Bootstrap)

**Goal:** Implement the main Access Logs view structure, displaying pending and today's logs as Bootstrap cards.

*   [X] **Flask Route (`/admin/reviews` or similar):**
    *   [X] Fetch pending reviews.
    *   [X] Fetch today's logs.
    *   [X] Pass both lists (`pending_logs`, `today_logs`) to the template context.
*   [X] **Template (`reviews.html` or similar, extending `base.html`):**
    *   [X] Add structure for sections (Pending, Today, Previous) using Bootstrap (e.g., headings, potentially `nav-tabs`).
    *   [X] **Pending Section:** Use `{% for log in pending_logs %}`.
        *   [X] Implement Bootstrap Card structure (`card`, `card-img-top`, `card-body`, `card-title`, etc.) inside a Bootstrap grid (`row`/`col-*`) within the loop.
        *   [X] Display image, key info, and "Details" link (`card-link`).
        *   [X] **Pagination:** Display all pending logs (no pagination needed initially).
    *   [X] **Today Section:** Use `{% for log in today_logs %}` and implement the same Bootstrap card structure.
        *   [X] **Pagination:** Display all logs from today (no pagination needed initially).

## Milestone 8: Admin Dashboard - Access Logs View (Previous Table - Bootstrap Table)

**Goal:** Implement the display for Previous logs using Bootstrap Table.

*   [X] **Flask Route (`/admin/reviews` or similar):**
    *   [X] Fetch previous *resolved* logs.
    *   [X] Add basic pagination logic (Flask-SQLAlchemy or manual). Pass list and pagination data to context.
*   [X] **Template (`reviews.html` or similar):**
    *   [X] **Previous Section:** Implement HTML `<table>` structure suitable for Bootstrap Table.
        *   [X] Add standard `<thead>` with columns: Image, Employee, Timestamp, Decision.
        *   [X] Use `<tbody>` with `{% for log in previous_logs %}` to create table rows (`<tr>`, `<td>`).
        *   [X] Include `<img>` tag for thumbnail in the Image column.
    *   [X] Add basic pagination links based on Flask data.
    *   [X] **Initialize Bootstrap Table:** Add necessary data attributes or minimal JS to initialize the table if needed for specific features (basic styling often works without JS init).

## Milestone 9: Admin Dashboard - Review Details View (Bootstrap)

**Goal:** Ensure the detailed review view renders correctly using Bootstrap layouts.

*   [X] **Flask Route (`/admin/reviews/<session_id>`):**
    *   [X] **Verify/Enhance:** `db_service.get_session_review_details` fetches necessary data.
    *   [X] Ensure route passes `details` dict to `review_details.html`.
*   [X] **Template (`review_details.html`):**
    *   [X] Use Jinja `{% if %}` blocks for conditional rendering.
    *   [X] Structure layouts using Bootstrap grid (`row`/`col-*`) or cards (`card`).
    *   [X] Use Bootstrap buttons (`btn`, `btn-success`, `btn-danger`) within HTML forms for Approve/Deny.
    *   [X] Use standard HTML radio buttons for `FACE_ONLY` selection, styled minimally or with basic Bootstrap form classes.

## Milestone 10: Admin Dashboard - Employee Management (CRUD - Basic - Bootstrap)

**Goal:** Implement basic employee views using Bootstrap tables and forms.

*   [X] **Flask Routes (`/admin/employees/...`):**
    *   [X] Implement `GET /admin/employees` (fetch all, render list).
    *   [X] Implement `GET /admin/employees/new` (render empty form).
    *   [X] Implement `POST /admin/employees` (handle create, redirect).
    *   [X] Implement placeholder routes for Edit/Delete.
*   [X] **Database:** Implement basic `db_service` methods for employees.
*   [X] **Templates:**
    *   [X] Create `employees_list.html`. Display employees in a Bootstrap `table` (`table`, `table-striped`, etc.). Add "Create" button (`btn`).
    *   [X] Create `employee_form.html`. Use Bootstrap form classes (`mb-3`, `form-label`, `form-control`).

## Milestone 11: Admin Dashboard - Employee Management (CRUD - Advanced - Bootstrap)

**Goal:** Implement Edit, Delete, and Photo/Embedding handling for employees using Bootstrap.

*   [X] **Flask Routes (`/admin/employees/...`):**
    *   [X] Implement `GET /admin/employees/<id>/edit` (fetch one, render pre-filled form).
    *   [X] Implement `POST /admin/employees/<id>/edit` (handle update, redirect).
    *   [X] Implement `POST /admin/employees/<id>/delete` (handle delete, redirect).
    *   [X] Enhance Create/Edit routes for photo upload/embedding.
*   [X] **Database:** Implement remaining `db_service` methods for employees.
*   [X] **Templates:**
    *   [X] Add Edit/Delete buttons (`btn btn-sm`) in `employees_list.html` table rows.
    *   [X] Add file input (`form-control`) to `employee_form.html`. Ensure form `enctype`.

## Milestone 12: Admin Dashboard - Emergency Status Display (Bootstrap)

**Goal:** Implement the emergency status display using a Bootstrap alert.

*   [X] **Flask API:**
    *   [X] Implement `GET /api/status/emergency` endpoint.
    *   [X] Implement/Verify state management for `is_emergency_active` flag.
*   [X] **Template (`base.html`):**
    *   [X] Add a hidden Bootstrap alert div (`<div id="emergency-banner" class="alert alert-danger d-none" role="alert">...</div>`).
    *   [X] Add JavaScript using `fetch`/`setInterval` to poll status endpoint and toggle the `d-none` class on the banner.

## Milestone 13: Styling & Refinement (Bootstrap Focus)

**Goal:** Ensure consistent Bootstrap styling and usability.

*   [X] **Bootstrap:** Review all pages and ensure consistent use of Bootstrap components and utility classes.
*   [X] **CSS:** Add minimal custom styles in `static/css/admin.css` only where Bootstrap doesn't cover specific needs.
*   [X] **Usability:** Test navigation, forms, review process.
*   [X] **Responsiveness:** Leverage Bootstrap's grid and utilities for basic responsiveness.


<!-- Supabase Object Storage Milestones -->


Okay, let's outline a step-by-step plan to migrate your image storage from the current PostgreSQL `BYTEA` columns to Supabase's Object Storage, while keeping your existing PostgreSQL database for metadata.

This approach leverages Supabase Storage for what it's good at (storing/serving files) and PostgreSQL for what *it's* good at (structured data and relations), effectively addressing the database connection pool exhaustion caused by serving image blobs.

---

## Milestone 14: Supabase Object Storage Integration

**Goal:** Migrate image storage from PostgreSQL BYTEA columns to Supabase Object Storage while keeping metadata in PostgreSQL.

*   [X] **Supabase Setup:**
    *   [X] Create Supabase project and storage bucket (`cses-images`).
    *   [X] Configure bucket access policies (public access recommended).
    *   [X] Get project URL and service role key.
*   [X] **Dependencies & Configuration:**
    *   [X] Add `supabase` to `requirements.txt`.
    *   [X] Add Supabase credentials to `.env`:
        ```dotenv
        SUPABASE_URL=YOUR_PROJECT_URL_HERE
        SUPABASE_SERVICE_KEY=YOUR_SERVICE_ROLE_KEY_HERE
        SUPABASE_BUCKET_NAME=cses-images
        ```
    *   [X] Update `config.py` to load Supabase settings.
*   [X] **Database Schema:**
    *   [X] Modify `employees` table to use `photo_url TEXT`.
    *   [X] Update `verification_images` table:
        *   [X] Remove `image_data BYTEA`.
        *   [X] Add `storage_url TEXT`.
    *   [X] Remove `verification_image_path` from `access_logs`.
*   [X] **Backend Implementation:**
    *   [X] Initialize Supabase client in Flask app.
    *   [X] Create image upload helper function.
    *   [X] Update MQTT service to upload images to Supabase.
    *   [X] Modify employee photo handling in admin routes.
    *   [X] Update database service methods:
        *   [X] Remove image data retrieval methods.
        *   [X] Update image URL handling in queries.
*   [X] **Frontend Updates:**
    *   [X] Update image display in all templates:
        *   [X] `reviews.html`
        *   [X] `review_details.html`
        *   [X] `employees_list.html`
        *   [X] `employee_form.html`
        *   [X] `_image_display.html`
    *   [X] Remove old image serving routes.
*   [X] **Testing:**
    *   [X] Verify end-to-end session flow.
    *   [X] Test employee photo upload/update.
    *   [X] Check image loading performance.
    *   [X] Monitor Supabase storage and API logs.
    *   [X] Confirm database connection pool improvements.

## Milestone 15: EMQX MQTT Broker Integration

**Goal:** Migrate MQTT communication from the local/Fly.io Mosquitto broker to a cloud-based EMQX Serverless deployment using TLS for secure connections.

*   [X] **EMQX Setup:**
    *   [X] Provision EMQX Cloud Serverless instance.
    *   [X] Note down Hostname and download CA Certificate (`emqxsl-ca.crt`).
*   [X] **Configuration Updates:**
    *   [X] **Python Backend:**
        *   [X] Update `api/config.py` default `MQTT_BROKER_ADDRESS` to `YOUR_EMQX_HOSTNAME` and `MQTT_BROKER_PORT` to `8883`. (Environment variables will override).
        *   [X] Place downloaded `emqxsl-ca.crt` into `api/certs/emqxsl-ca.crt`.
        *   [X] Ensure `api/certs/emqxsl-ca.crt` is committed to the repository (NOT in `.gitignore`).
    *   [X] **ESP32-WROVER:**
        *   [X] Update `ESP32-WROVER/src/config.h` to define `MQTT_BROKER_ADDRESS` as `YOUR_EMQX_HOSTNAME` and `MQTT_PORT` as `8883`.
        *   [X] Add `EMQX_CA_CERT_PEM` definition in `ESP32-WROVER/src/config.h` containing `YOUR_EMQX_CA_CERT_CONTENT`.
    *   [X] **Arduino Uno R4:**
        *   [X] Update `ServoArduinoUno/src/config.h` to define `MQTT_BROKER` as `YOUR_EMQX_HOSTNAME` and `MQTT_PORT` as `8883`.
        *   [X] Add `EMQX_CA_CERT_PEM` definition in `ServoArduinoUno/src/config.h` containing `YOUR_EMQX_CA_CERT_CONTENT`.
    *   **Note:** The Uno R4 WiFi firmware includes a built-in CA certificate bundle. For default EMQX Cloud connections (which use Let's Encrypt certificates included in the bundle), manual loading via `setCACert` is not required. The correct secure client class is `WiFiSSLClient` from `<WiFiSSLClient.h>`, not `WiFiClientSecure`.
*   [X] **Python Backend Code (`api/services/mqtt_service.py`):**
    *   [X] Import `ssl`.
    *   [X] Modify `MQTTService.__init__` to enable TLS using `self.client.tls_set(ca_certs="certs/emqxsl-ca.crt", cert_reqs=ssl.CERT_REQUIRED)`.
    *   [X] Verify `self.client.connect()` uses the configured port (8883).
*   [X] **ESP32-WROVER Code (`ESP32-WROVER/src/mqtt/`):**
    *   [X] Update `mqtt.h`: Replace `WiFiClient` with `WiFiClientSecure`.
    *   [X] Update `mqtt.cpp`:
        *   [X] Include `<WiFiClientSecure.h>`.
        *   [X] Instantiate client as `WiFiClientSecure`.
        *   [X] Add `wifiClient.setCACert(EMQX_CA_CERT_PEM)` before connecting.
        *   [X] Ensure `mqttClient.setServer()` uses the hostname from `config.h` and port 8883.
*   [X] **Arduino Uno R4 Code (`ServoArduinoUno/src/mqtt/`):**
    *   [X] Create a test file similar to `ESP32-WROVER/src/tests/test_mqtt_secure_connection.cpp` to test the secure connection to the EMQX cloud broker.
    *   [X] Update `mqtt.h`: Replace `WiFiClient` with `WiFiSSLClient`.
    *   [X] Update `mqtt.cpp`:
        *   [X] Include `<WiFiSSLClient.h>`.
        *   [X] Instantiate client as `WiFiSSLClient`.
        *   [X] Ensure `mqttClient.setServer()` uses the hostname from `config.h` and port 8883.
    *   **Note:** The Uno R4 WiFi firmware includes a built-in CA certificate bundle. For default EMQX Cloud connections (which use Let's Encrypt certificates included in the bundle), manual loading via `setCACert` is not required. The correct secure client class is `WiFiSSLClient` from `<WiFiSSLClient.h>`, not `WiFiClientSecure`.
*   [ ] **Testing:**
    *   [X] Verify Python backend connects successfully to EMQX.
    *   [ ] Verify ESP32-WROVER connects successfully to EMQX.
    *   [ ] Verify Arduino Uno R4 connects successfully to EMQX.
    *   [ ] Test end-to-end message publishing and receiving across all clients via EMQX.
*   [ ] **(Optional) Deprecate Old Broker:**
    *   [ ] Once EMQX is confirmed stable, stop/remove the Fly.io/Mosquitto deployment (`mqtt_broker` directory, `fly.toml`, etc.).

## Moving Face Recognition off of the ESP32-WROVER

## Milestone 16: Centralize Face Embedding Generation on Backend

**Goal:** Remove reliance on the ESP32-WROVER's onboard face detection flag. Always attempt face embedding generation via the backend DeepFace service for every session attempt that includes an image, shifting the "is there a usable face?" decision entirely to the backend.

*   **Task 1: Modify ESP32 Firmware (`ESP32-WROVER/src/main.cpp`)**
    *   **[ ] `handleImageCaptureState()`:**
        *   Remove the assignment to `faceDetectedInSession` based on `detection.found()`.
        *   The loop should still aim to capture the best possible frame, but the outcome of `detection.found()` no longer determines a flag passed in the payload. The primary goal is now just `validFrameCaptured = true`.
    *   **[ ] `handleSessionState()`:**
        *   In the `jsonDoc` creation, remove the line `jsonDoc["face_detected"] = faceDetectedInSession;`. This field should no longer be part of the MQTT payload sent to the `campus/security/session` topic.
    *   **[ ] Verification:** Compile and flash the updated firmware to the ESP32-WROVER. Monitor serial output during a session to confirm images are captured and sent *without* the `face_detected` key in the JSON payload.

*   **Task 2: Modify API Backend (`api/services/mqtt_service.py`)**
    *   **[ ] `_handle_session_message()`:**
        *   Locate the section handling image processing (around line 431).
        *   Remove the `if session_data.face_detected:` condition and the corresponding `else:` block that skips embedding generation.
        *   Ensure the call `new_embedding = self.face_client.get_embedding(session_data.image)` is executed *directly* within the `if session_data.image:` block (after decoding and successful Supabase upload check `if storage_url:`), effectively attempting embedding generation for *every* session that provides an image.
    *   **[ ] Review Logic:** Double-check the subsequent verification logic (around lines 515 onwards) that uses `if employee_record and new_embedding is not None:`, `elif new_embedding is not None:`, etc. Confirm that it correctly handles the flow based solely on whether `new_embedding` successfully received a value from `get_embedding` or remained `None`, without reference to any (now removed) `face_detected` flag.

*   **Task 3: Modify API Data Model (`api/models/session.py`)**
    *   **[ ] `Session` Pydantic Model:** Remove the `face_detected: bool` field definition from the `Session` Pydantic class, as this field is no longer expected in the incoming MQTT payload.

*   **Task 4: Testing and Verification**
    *   **[ ] Docker:** Rebuild and restart the API container (`docker compose build api && docker compose up -d api`).
    *   **[ ] Test Case: Image, No RFID:** Using an MQTT client tool or a test script, publish a message to `campus/security/session` with a valid `session_id`, `timestamp`, `image` (containing a known face), etc., but *no* `rfid_tag`. Verify in API logs:
        *   `get_embedding` is called.
        *   An embedding is successfully obtained.
        *   The `FACE_ONLY_PENDING_REVIEW` logic branch is entered.
        *   `find_similar_embeddings` is called.
        *   `log_access_attempt` is called with `verification_method='FACE_ONLY_PENDING_REVIEW'`.
    *   **[ ] Test Case: Image (No Face), No RFID:** Publish a message similar to the above, but use an `image` known to *not* contain a detectable face. Verify in API logs:
        *   `get_embedding` is called.
        *   `get_embedding` returns `None` (or fails gracefully).
        *   The `NO_FACE_OR_RFID` logic branch is entered.
        *   `log_access_attempt` is called with `verification_method='NO_FACE_OR_RFID'`.
    *   **[ ] Test Case: Image, Known RFID:** Publish a message with a valid `image` (known face) and a known, matching `rfid_tag`. Verify in API logs:
        *   `get_embedding` is called and returns an embedding.
        *   `get_employee_by_rfid` returns an employee record.
        *   `verify_embeddings` is called.
        *   The `RFID+FACE` logic branch is entered.
        *   `log_access_attempt` is called (likely with `access_granted=True`).
    *   **[ ] Test Case: Image (No Face), Known RFID:** Publish a message with an image containing *no* face but a known, matching `rfid_tag`. Verify in API logs:
        *   `get_embedding` is called and returns `None`.
        *   `get_employee_by_rfid` returns an employee record.
        *   The `RFID_ONLY_PENDING_REVIEW` logic branch is entered.
        *   `log_access_attempt` is called with `verification_method='RFID_ONLY_PENDING_REVIEW'`.
    *   **[ ] End-to-End:** Trigger sessions using the actual ESP32 with the updated firmware. Observe the behavior in the API logs and the admin dashboard's review sections for different scenarios (face present/absent, RFID present/absent).

*   **Task 5: (Optional) Infrastructure Considerations**
    *   **[ ] Monitor DeepFace Service:** During and after testing, monitor the CPU and memory usage of the `deepface_service` container using `docker stats`. If usage is consistently high or causing slowdowns, consider increasing resource limits/reservations in `docker-compose.yml`.

---