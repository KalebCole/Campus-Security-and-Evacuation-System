# Frontend Admin Dashboard Overview (React)

## 1. Goal

Replace the existing Flask/Jinja-based admin interface with a modern, interactive dashboard built using React. This dashboard will reside in the `frontend/` directory and interact with the backend Flask API (`api/`) to manage access logs and employees.

## 2. Core Features & Navigation

*   **Single Page Application (SPA):** Built with React.
*   **Technology Stack:**
    *   **Framework:** React.js (using JavaScript)
    *   **UI Components/Styling:** shadcn/ui
    *   **Routing:** `react-router-dom`
    *   **State Management:** React Hooks (`useState`, `useEffect`, `useContext`) initially. Consider Zustand/Jotai if complexity increases.
    *   **API Communication:** `fetch` API or `axios`.
*   **Side Navigation Bar:**
    *   Toggleable via a hamburger icon.
    *   **Access Logs:** Icon link to the main access log view.
        *   **Notification Badge:** A small indicator (e.g., red circle) on the Access Logs icon displaying the current count of pending reviews. 
            *   **Implementation:** Uses `setInterval` within a React Context or top-level component to periodically poll `GET /admin/reviews/pending/count` and update a shared state.
    *   **Employees:** Icon link to the Employee management view (CRUD).
*   **Routing:** Use a library like `react-router-dom` for navigation between views.

## 3. Access Log Views

The main view for managing access logs, split into logical sections:

*   **Tabs/Sections:**
    *   **Pending Reviews:** Displays logs with `review_status = 'pending'`. Requires manual admin action. (Pagination will be needed for large datasets.)
    *   **Today's Logs:** Displays all logs (pending, approved, denied) from the current day. (Pagination will be needed for large datasets.)
    *   **Previous Logs:** Displays all historical logs (approved, denied) prior to today with a show more button to expand the table.
*   **Layout:**
    *   **Pending & Today's:** Use a **Card Gallery** layout. Each card represents one access log event.
        *   **Log Card Component:**
            *   Displays the captured verification image prominently at the top.
            *   Shows key details below the image: Timestamp, Verification Method (e.g., `RFID_ONLY_PENDING_REVIEW`), Employee Name (if associated), current Status (`pending`, `approved`, `denied`).
            *   Clickable to navigate to the detailed review view.
        *   (Consider a subtle visual distinction for pending cards).
    *   **Previous Logs:** Use a **Table** layout for density.
        *   **Columns:** Captured Image Thumbnail (clickable?), Employee Name (or "N/A"), Timestamp, Status (Approved/Denied), Verification Method.
            *   Pagination will be needed for large datasets. This will be implemented as a show more button that expands the table.

## 4. Review Details View

This view appears when an admin clicks on a log card (especially a pending one) to take action. The layout adapts based on the `verification_method` of the log.

*   **Common Elements:** Always show core log details (Timestamp, Session ID, etc.) and Approve/Deny action buttons.
*   **Layout Variations:**
    *   **`RFID_ONLY_PENDING_REVIEW`:** (RFID detected, no face detected by ESP32)
        *   Side-by-side display:
            *   **Left Card:** Captured Image (labeled "Captured Image - No Face Detected") + Log details.
            *   **Right Card:** Associated Employee's reference photo + Employee details (Name, ID). Fetched based on the RFID tag linked to the log.
        *   **Actions:** Approve / Deny buttons below the cards.
            *   `Deny` button is always enabled and doesn't require a selection.
    *   **`FACE_ONLY_PENDING_REVIEW`:**
        *   **Top Card:** Captured Image (labeled "Captured Image - No RFID Presented") + Log details.
        *   **Below:** Section labeled "Potential Matches".
            *   Displays cards for the Top 3 potential employee matches (Image, Name, Confidence Score) based on face similarity search results provided by the API.
            *   Matches are **selectable** (e.g., radio buttons or clicking the card highlights it).
        *   **Actions:** Approve / Deny buttons.
            *   `Approve` button is initially disabled.
            *   Selecting a potential match enables the `Approve` button. Clicking Approve sends the selected `employee_id` along with the approval to the backend API.
            *   `Deny` button is always enabled and doesn't require a selection.
    *   **`FACE_VERIFICATION_FAILED`:** (RFID detected, face detected, but face embedding match confidence below threshold)
        *   Side-by-side display (similar to RFID_ONLY):
            *   **Left Card:** Captured Image (labeled "Captured Image - Verification Failed") + Log details (including confidence score).
            *   **Right Card:** Associated Employee's reference photo (from RFID match) + Employee details.
        *   **Actions:** Approve / Deny buttons.

*   **Approve Action:**
    *   Calls the backend API endpoint (`/admin/reviews/<session_id>/approve`).
    *   If the API call is successful, the API service publishes a message to the `campus/security/unlock` MQTT topic.
    *   Updates the log status in the UI and navigates back to the main log view (or updates the current view).
*   **Deny Action:**
    *   Calls the backend API endpoint (`/admin/reviews/<session_id>/deny`).
    *   Updates the log status in the UI and navigates back.

## 5. Employee Management View (CRUD)

A standard CRUD interface for managing employees in the database.

*   **View:** Display employees in a table (ID, Name, Email/Department?, Photo Thumbnail).
*   **Create:** Form to add a new employee (Name, other details, potentially upload a reference photo).
*   **Update:** Form to edit an existing employee's details.
*   **Delete:** Button to remove an employee record.
*   **API Interaction:** Requires dedicated backend API endpoints (e.g., `/admin/employees`, `/admin/employees/<id>`) supporting GET, POST, PUT, DELETE.

## 6. Emergency Status Display

*   **Requirement:** Display a persistent, clear visual indicator (e.g., a banner at the top of the dashboard) when the system is in an emergency state.
*   **Mechanism:**
    *   **API Polling:** The React frontend will periodically poll a new backend API endpoint (e.g., `/api/status/emergency`).
        *   **Implementation:** Uses `setInterval` within a React Context or top-level component to periodically poll `GET /api/status/emergency`. The API endpoint reflects the state based on whether the API service has received a message on the `/campus/security/emergency` MQTT topic.
    *   This endpoint will return the current emergency status (e.g., `{ "emergency_active": true/false }`).
    *   The frontend updates a shared state based on the API response, which conditionally renders a persistent visual indicator (e.g., banner).
    *   The emergency status will be displayed from the ntfy notification service (via the API) when the emergency button is triggered and the api receives the message over the `/campus/security/emergency` topic.

## 7. Required API Endpoints (Summary - Needs Verification/Creation)

*   `GET /admin/reviews/pending/count`: Returns the number of pending reviews (for the badge).
*   `GET /admin/reviews?status=pending`: Returns list of pending review logs (for Pending tab).
*   `GET /admin/reviews?date=today`: Returns list of logs from today (for Today tab).
*   `GET /admin/reviews?status=resolved&page=<num>`: Returns paginated list of previously resolved logs (for Previous tab).
*   `GET /admin/reviews/<session_id>`: Returns detailed data for a specific log, including potential matches if `FACE_ONLY`. (Existing, but might need to ensure potential matches are included).
*   `POST /admin/reviews/<session_id>/approve`: Approves a log (Existing, ensure it handles `selected_employee_id` from form data for FACE_ONLY).
*   `POST /admin/reviews/<session_id>/deny`: Denies a log (Existing).
*   `GET /admin/image/<session_id>`: Serves the verification image (Existing).
*   `GET /admin/employees`: List all employees. (NEW)
*   `POST /admin/employees`: Create a new employee. (NEW)
*   `GET /admin/employees/<employee_id>`: Get details for one employee. (NEW)
*   `PUT /admin/employees/<employee_id>`: Update an employee. (NEW)
*   `DELETE /admin/employees/<employee_id>`: Delete an employee. (NEW)
*   `GET /api/status/emergency`: Returns current emergency status `{ "emergency_active": true/false }`. (NEW)

## 8. Styling

*   Use a UI library (e.g., Material UI, Chakra UI, Tailwind CSS) for consistent styling and pre-built components.
*   Aim for a clean, professional, and responsive design.
*   **Chosen Library:** shadcn/ui (backed by Tailwind CSS)

## 1. Goal

Replace the existing Flask/Jinja-based admin interface with a modern, interactive dashboard built using React. This dashboard will reside in the `frontend/` directory and interact with the backend Flask API (`api/`) to manage access logs and employees.

## 2. Core Features & Navigation

*   **Single Page Application (SPA):** Built with React.
*   **Technology Stack:**
    *   **Framework:** React.js (using JavaScript)
    *   **UI Components/Styling:** shadcn/ui
    *   **Routing:** `react-router-dom`
    *   **State Management:** React Hooks (`useState`, `useEffect`, `useContext`) initially. Consider Zustand/Jotai if complexity increases.
    *   **API Communication:** `fetch` API or `axios`.
*   **Side Navigation Bar:**
    *   Toggleable via a hamburger icon.
    *   **Access Logs:** Icon link to the main access log view.
        *   **Notification Badge:** A small indicator (e.g., red circle) on the Access Logs icon displaying the current count of pending reviews. 
            *   **Implementation:** Uses `setInterval` within a React Context or top-level component to periodically poll `GET /admin/reviews/pending/count` and update a shared state.
    *   **Employees:** Icon link to the Employee management view (CRUD).
*   **Routing:** Use a library like `react-router-dom` for navigation between views.

## 3. Access Log Views

The main view for managing access logs, split into logical sections:

*   **Tabs/Sections:**
    *   **Pending Reviews:** Displays logs with `review_status = 'pending'`. Requires manual admin action. (Pagination will be needed for large datasets.)
    *   **Today's Logs:** Displays all logs (pending, approved, denied) from the current day. (Pagination will be needed for large datasets.)
    *   **Previous Logs:** Displays all historical logs (approved, denied) prior to today with a show more button to expand the table.
*   **Layout:**
    *   **Pending & Today's:** Use a **Card Gallery** layout. Each card represents one access log event.
        *   **Log Card Component:**
            *   Displays the captured verification image prominently at the top.
            *   Shows key details below the image: Timestamp, Verification Method (e.g., `RFID_ONLY_PENDING_REVIEW`), Employee Name (if associated), current Status (`pending`, `approved`, `denied`).
            *   Clickable to navigate to the detailed review view.
        *   (Consider a subtle visual distinction for pending cards).
    *   **Previous Logs:** Use a **Table** layout for density.
        *   **Columns:** Captured Image Thumbnail (clickable?), Employee Name (or "N/A"), Timestamp, Status (Approved/Denied), Verification Method.
            *   Pagination will be needed for large datasets. This will be implemented as a show more button that expands the table.

## 4. Review Details View

This view appears when an admin clicks on a log card (especially a pending one) to take action. The layout adapts based on the `verification_method` of the log.

*   **Common Elements:** Always show core log details (Timestamp, Session ID, etc.) and Approve/Deny action buttons.
*   **Layout Variations:**
    *   **`RFID_ONLY_PENDING_REVIEW`:** (RFID detected, no face detected by ESP32)
        *   Side-by-side display:
            *   **Left Card:** Captured Image (labeled "Captured Image - No Face Detected") + Log details.
            *   **Right Card:** Associated Employee's reference photo + Employee details (Name, ID). Fetched based on the RFID tag linked to the log.
        *   **Actions:** Approve / Deny buttons below the cards.
            *   `Deny` button is always enabled and doesn't require a selection.
    *   **`FACE_ONLY_PENDING_REVIEW`:**
        *   **Top Card:** Captured Image (labeled "Captured Image - No RFID Presented") + Log details.
        *   **Below:** Section labeled "Potential Matches".
            *   Displays cards for the Top 3 potential employee matches (Image, Name, Confidence Score) based on face similarity search results provided by the API.
            *   Matches are **selectable** (e.g., radio buttons or clicking the card highlights it).
        *   **Actions:** Approve / Deny buttons.
            *   `Approve` button is initially disabled.
            *   Selecting a potential match enables the `Approve` button. Clicking Approve sends the selected `employee_id` along with the approval to the backend API.
            *   `Deny` button is always enabled and doesn't require a selection.
    *   **`FACE_VERIFICATION_FAILED`:** (RFID detected, face detected, but face embedding match confidence below threshold)
        *   Side-by-side display (similar to RFID_ONLY):
            *   **Left Card:** Captured Image (labeled "Captured Image - Verification Failed") + Log details (including confidence score).
            *   **Right Card:** Associated Employee's reference photo (from RFID match) + Employee details.
        *   **Actions:** Approve / Deny buttons.

*   **Approve Action:**
    *   Calls the backend API endpoint (`/admin/reviews/<session_id>/approve`).
    *   If the API call is successful, the API service publishes a message to the `campus/security/unlock` MQTT topic.
    *   Updates the log status in the UI and navigates back to the main log view (or updates the current view).
*   **Deny Action:**
    *   Calls the backend API endpoint (`/admin/reviews/<session_id>/deny`).
    *   Updates the log status in the UI and navigates back.

## 5. Employee Management View (CRUD)

A standard CRUD interface for managing employees in the database.

*   **View:** Display employees in a table (ID, Name, Email/Department?, Photo Thumbnail).
*   **Create:** Form to add a new employee (Name, other details, potentially upload a reference photo).
*   **Update:** Form to edit an existing employee's details.
*   **Delete:** Button to remove an employee record.
*   **API Interaction:** Requires dedicated backend API endpoints (e.g., `/admin/employees`, `/admin/employees/<id>`) supporting GET, POST, PUT, DELETE.

## 6. Emergency Status Display

*   **Requirement:** Display a persistent, clear visual indicator (e.g., a banner at the top of the dashboard) when the system is in an emergency state.
*   **Mechanism:**
    *   **API Polling:** The React frontend will periodically poll a new backend API endpoint (e.g., `/api/status/emergency`).
        *   **Implementation:** Uses `setInterval` within a React Context or top-level component to periodically poll `GET /api/status/emergency`. The API endpoint reflects the state based on whether the API service has received a message on the `/campus/security/emergency` MQTT topic.
    *   This endpoint will return the current emergency status (e.g., `{ "emergency_active": true/false }`).
    *   The frontend updates a shared state based on the API response, which conditionally renders a persistent visual indicator (e.g., banner).
    *   The emergency status will be displayed from the ntfy notification service (via the API) when the emergency button is triggered and the api receives the message over the `/campus/security/emergency` topic.

## 7. Required API Endpoints (Summary - Needs Verification/Creation)

*   `GET /admin/reviews/pending/count`: Returns the number of pending reviews (for the badge).
*   `GET /admin/reviews?status=pending`: Returns list of pending review logs (for Pending tab).
*   `GET /admin/reviews?date=today`: Returns list of logs from today (for Today tab).
*   `GET /admin/reviews?status=resolved&page=<num>`: Returns paginated list of previously resolved logs (for Previous tab).
*   `GET /admin/reviews/<session_id>`: Returns detailed data for a specific log, including potential matches if `FACE_ONLY`. (Existing, but might need to ensure potential matches are included).
*   `POST /admin/reviews/<session_id>/approve`: Approves a log (Existing, ensure it handles `selected_employee_id` from form data for FACE_ONLY).
*   `POST /admin/reviews/<session_id>/deny`: Denies a log (Existing).
*   `GET /admin/image/<session_id>`: Serves the verification image (Existing).
*   `GET /admin/employees`: List all employees. (NEW)
*   `POST /admin/employees`: Create a new employee. (NEW)
*   `GET /admin/employees/<employee_id>`: Get details for one employee. (NEW)
*   `PUT /admin/employees/<employee_id>`: Update an employee. (NEW)
*   `DELETE /admin/employees/<employee_id>`: Delete an employee. (NEW)
*   `GET /api/status/emergency`: Returns current emergency status `{ "emergency_active": true/false }`. (NEW)

## 8. Styling

*   Use a UI library (e.g., Material UI, Chakra UI, Tailwind CSS) for consistent styling and pre-built components.
*   Aim for a clean, professional, and responsive design.
*   **Chosen Library:** shadcn/ui (backed by Tailwind CSS)
