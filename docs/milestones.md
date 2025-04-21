# Project Milestones - Arduino Mega Central Control Architecture

This document outlines the milestones required to transition the CSES project to the new architecture where the Arduino Mega acts as the central sensor and control hub, communicating directly with the ESP32-CAM via wired signals.

**Current State:**
*   Arduino code exists for Uno R4 (needs porting to Mega).
*   ESP32 code exists (needs modification for wired signals).
*   ESP32 reads motion sensor directly.
*   ESP32 subscribes to `/rfid` MQTT topic.
*   Arduino publishes RFID data to `/rfid` MQTT topic.
*   Project Overview and ESP32 README reflect the old architecture.

**Target State:**
*   Arduino Mega handles all sensor inputs (Motion, RFID, Emergency).
*   Arduino Mega controls servo via connected Arduino Uno.
*   Arduino Mega sends digital signals to ESP32 for Motion and RFID detection events.
*   ESP32 receives signals from Mega via input pins.
*   ESP32 packages session data (including RFID status based on Mega signal) and sends to `/session` MQTT topic.
*   `/rfid` MQTT topic is deprecated.
*   Documentation reflects the new architecture.

---
# FRONTEND MILESTONES

## Milestone 6: Frontend Admin Dashboard - Setup & Core Layout (React)

**Goal:** Initialize the React project and implement the main application shell and navigation.
**Reference:** [docs/frontend-overview.md](./frontend-overview.md)

*   [X] **Frontend: Project Initialization:**
    *   [X] Initialize React project in `frontend/` (Vite recommended: `npm create vite@latest frontend -- --template react-ts` or `react`).
    *   [X] Set up project structure (`src/components`, `src/pages`, `src/hooks`, `src/services`, `src/contexts`, `src/lib`, etc.).
*   [X] **Frontend: Dependencies & Configuration:**
    *   [X] Install `react-router-dom`, `tailwindcss`, `lucide-react` (or other icon library).
    *   [X] Initialize Tailwind CSS (`tailwind.config.js`, `postcss.config.js`, `./src/index.css`).
    *   [X] Initialize `shadcn/ui` CLI (`npx shadcn-ui@latest init`). Choose style, base color, css variables, etc.
*   [] **Frontend: Core Layout & Routing:**
    *   [ ] Implement main App layout component (`src/App.jsx`).
    *   [ ] Configure basic routing using `react-router-dom` (`src/main.jsx` or dedicated router file).
    *   [ ] Implement `SideNavBar` component (using `shadcn/ui` `Sheet` for toggleable drawer, `Button` for icon).
        *   [ ] Add placeholder links/icons for "Access Logs" and "Employees".
    *   [ ] Create placeholder page components: `AccessLogsPage`, `EmployeesPage`, `NotFoundPage`.
    *   [ ] Configure basic API client service (`src/services/api.js`) with base URL from environment variable.
*   [ ] **Backend API:** Ensure API is runnable and base URL is accessible/known.
*   [ ] **Database:** No changes required for this stage.

## Milestone 7: Frontend - Access Logs View & Pending Count

**Goal:** Implement the main Access Logs view structure, display pending logs, and implement the notification badge.

*   [ ] **Backend API:**
    *   [ ] **Implement/Verify:** `GET /admin/reviews/pending/count` endpoint.
    *   [ ] **Implement/Verify:** `GET /admin/reviews?status=pending&page=<num>` endpoint (paginated). Ensure it returns necessary fields for cards (session_id, timestamp, verification_method, status, associated employee name, image endpoint/URL).
    *   [ ] **Verify:** `GET /admin/image/<session_id>` endpoint serves images correctly.
    *   [ ] **Modify:** Existing `GET /admin/reviews/pending` route to return JSON (not HTML) and add pagination support.
*   [ ] **Frontend: State Management:**
    *   [ ] Create a global context (`AppProvider` or `NotificationProvider`) for shared state like pending count and potentially emergency status later.
*   [ ] **Frontend: Pending Count Badge:**
    *   [ ] Implement polling logic (`setInterval` in Context Provider `useEffect`) to fetch from `GET /admin/reviews/pending/count`.
    *   [ ] Store count in context state.
    *   [ ] Update `SideNavBar` component to consume count from context and display a badge (e.g., `shadcn/ui` `Badge` or styled div).
*   [ ] **Frontend: Access Logs Page Structure:**
    *   [ ] Implement `AccessLogsPage` component.
    *   [ ] Add `shadcn/ui` `Tabs` component for "Pending", "Today", "Previous".
*   [ ] **Frontend: Pending Logs Display:**
    *   [ ] Create `LogCard` component (using `shadcn/ui` `Card`, `CardHeader`, `CardContent`, `CardFooter`). Include `img` tag pointing to `/admin/image/<session_id>`.
    *   [ ] Implement data fetching hook (`useFetchPendingLogs`) for `GET /admin/reviews?status=pending&page=<num>`.
    *   [ ] Display fetched pending logs in the "Pending" tab using `LogCard` components in a grid/flex layout.
    *   [ ] Implement basic pagination or "Load More" for pending logs if API supports it.
*   [ ] **Database:** Ensure DB queries for pending count and logs are efficient.

## Milestone 8: Frontend - Today & Previous Logs Display

**Goal:** Implement the display for Today's logs (gallery) and Previous logs (table).

*   [ ] **Backend API:**
    *   [ ] **Implement/Verify:** `GET /admin/reviews?date=today&page=<num>` endpoint (paginated). Returns logs for the current date.
    *   [ ] **Implement/Verify:** `GET /admin/reviews?status=resolved&page=<num>` endpoint (paginated). Returns 'approved'/'denied' logs, ordered desc by timestamp.
    *   [ ] **Implement:** Add query parameter handling (`date`, `status`, `page`) to the core `GET /admin/reviews` route (or a new route if preferred).
    *   [ ] **Implement:** Database service methods to support filtering by date and status with pagination (`LIMIT`/`OFFSET`).
*   [ ] **Frontend: Today's Logs Display:**
    *   [ ] Implement data fetching hook (`useFetchTodayLogs`) for `GET /admin/reviews?date=today&page=<num>`.
    *   [ ] Display fetched logs in the "Today" tab using the `LogCard` gallery layout.
    *   [ ] Implement pagination/"Load More" similar to Pending logs.
*   [ ] **Frontend: Previous Logs Display:**
    *   [ ] Implement data fetching hook (`useFetchPreviousLogs`) for `GET /admin/reviews?status=resolved&page=<num>`.
    *   [ ] Implement table layout in the "Previous" tab using `shadcn/ui` `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`.
    *   [ ] Define table columns: Image Thumbnail, Employee Name, Timestamp, Status, Verification Method.
    *   [ ] Implement "Show More" button logic to fetch the next page and append data.
*   [ ] **Database:** Ensure DB queries for date filtering and resolved status filtering are efficient.

## Milestone 9: Frontend - Review Details View (Layouts & Data)

**Goal:** Implement the detailed view for a single log entry, adapting layout based on review type.

*   [ ] **Backend API:**
    *   [ ] **Implement/Verify:** `GET /admin/reviews/<session_id>` endpoint. Ensure it returns:
        *   Full `access_log` details.
        *   *Conditional:* Associated `employee` details (name, photo_url) if log has `employee_id` set (for `RFID_ONLY`, `FACE_VERIFICATION_FAILED`).
        *   *Conditional:* List of `potential_matches` (employee_id, name, confidence, photo_url) if `FACE_ONLY`.
        *   URL/endpoint for the captured verification image.
    *   [ ] **Modify:** Existing `GET /admin/reviews/<uuid:session_id>` route to return JSON (not HTML).
    *   [ ] **Modify:** `db_service.get_session_review_details` to perform conditional fetching of employee/potential matches and structure the JSON output correctly.
*   [ ] **Frontend: Routing & Navigation:**
    *   [ ] Add route for `/reviews/:sessionId` pointing to `ReviewDetailsPage` component.
    *   [ ] Make `LogCard` components clickable, navigating to the corresponding details page.
*   [ ] **Frontend: Review Details Page:**
    *   [ ] Implement `ReviewDetailsPage` component.
    *   [ ] Fetch detailed log data using `useParams` hook to get `sessionId` and calling the API (`GET /admin/reviews/<session_id>`).
    *   [ ] Implement conditional rendering logic based on `log.verification_method`.
    *   [ ] Create reusable `CapturedImageCard` and `EmployeeCard` components.
    *   [ ] Implement layout for `RFID_ONLY_PENDING_REVIEW` (side-by-side cards).
    *   [ ] Implement layout for `FACE_ONLY_PENDING_REVIEW` (captured image card + list/grid of selectable potential match `EmployeeCard`s).
    *   [ ] Implement layout for `FACE_VERIFICATION_FAILED` (side-by-side cards).
    *   [ ] Add placeholder Approve/Deny buttons (functionality in next milestone).
*   [ ] **Database:** Ensure query for `GET /admin/reviews/<session_id>` correctly performs joins and potential vector search based on the verification method.

## Milestone 10: Frontend - Review Details View (Actions)

**Goal:** Implement the Approve and Deny functionality on the Review Details page.

*   [ ] **Backend API:**
    *   [ ] **Verify:** `POST /admin/reviews/<session_id>/approve` endpoint correctly handles request body (including optional `selected_employee_id`), updates DB (`review_status`, potentially `employee_id`), and triggers MQTT unlock.
    *   [ ] **Verify:** `POST /admin/reviews/<session_id>/deny` endpoint correctly updates DB (`review_status`).
    *   [ ] **Modify:** Existing `POST /admin/reviews/.../approve` and `POST /admin/reviews/.../deny` routes to primarily accept JSON payloads (`request.get_json()`) instead of/in addition to form data.
*   [ ] **Frontend: Actions & State:**
    *   [ ] Implement state management within `ReviewDetailsPage` for `FACE_ONLY` selection (which potential match is selected).
    *   [ ] Implement selection logic for potential match cards (e.g., visually highlight selected card, update state).
    *   [ ] Add `ApproveButton` and `DenyButton` components (use `shadcn/ui` `Button`, potentially async handling state).
    *   [ ] Disable Approve button for `FACE_ONLY` if no match is selected.
    *   [ ] Implement `handleApprove` function: constructs API request (including `selected_employee_id` if needed), calls API, handles response (show success/error toast using `shadcn/ui` `Toast`), potentially navigates back on success.
    *   [ ] Implement `handleDeny` function: calls API, handles response, potentially navigates back.
*   [ ] **Database:** Ensure `UPDATE` statements in backend API for approve/deny are correct.

## Milestone 11: Frontend - Employee Management (CRUD)

**Goal:** Implement the view and functionality to manage employees.

*   [ ] **Backend API:**
    *   [ ] **Implement:** `GET /admin/employees` (list all, paginated?).
    *   [ ] **Implement:** `POST /admin/employees` (create new, handle form data including optional photo upload, trigger embedding generation).
    *   [ ] **Implement:** `GET /admin/employees/<employee_id>` (get single for edit).
    *   [ ] **Implement:** `PUT /admin/employees/<employee_id>` (update, handle photo update/embedding regeneration).
    *   [ ] **Implement:** `DELETE /admin/employees/<employee_id>` (delete).
    *   [ ] **Implement:** New routes in `admin.py` (or a new `employees.py` blueprint) for all CRUD operations.
    *   [ ] **Implement:** New methods in `database.py` for Employee CRUD logic (Create, Read, Update, Delete).
    *   [ ] **Implement:** Logic in Create/Update to handle image storage and trigger embedding via `FaceRecognitionClient`.
*   [ ] **Frontend: Employee Page & Table:**
    *   [ ] Implement `EmployeesPage` component.
    *   [ ] Implement table using `shadcn/ui` `Table` to display employees (fetch from `GET /admin/employees`). Columns: ID, Name, Email, Role, RFID Tag, Photo Thumbnail, Actions (Edit/Delete buttons).
    *   [ ] Add "Create New Employee" button.
*   [ ] **Frontend: Employee Form (Create/Edit):**
    *   [ ] Implement reusable `EmployeeForm` component (likely within a `shadcn/ui` `Dialog` or `Sheet`).
    *   [ ] Include form fields (Name, Email, Role, RFID Tag) using `shadcn/ui` `Input`, `Label`, etc. Add file input for photo.
    *   [ ] Handle form submission for Create (`POST`) and Edit (`PUT`).
*   [ ] **Frontend: Delete Action:**
    *   [ ] Implement `handleDelete` function triggered by delete button in table row.
    *   [ ] Use `shadcn/ui` `AlertDialog` for confirmation before calling `DELETE /admin/employees/<id>`.
    *   [ ] Update table UI on successful deletion.
*   [ ] **Database:** Ensure backend API correctly implements CRUD operations on `employees` table, including handling image storage and embedding logic.

## Milestone 12: Frontend - Emergency Status Display

**Goal:** Implement the real-time display of the system's emergency status.

*   [ ] **Backend API:**
    *   [ ] **Implement:** `GET /api/status/emergency` endpoint. Reads the current emergency state maintained by the API service (updated via MQTT subscriber).
    *   [ ] **Implement:** New route (e.g., in `routes/system.py` or similar) for the status endpoint.
    *   [ ] **Implement:** State management (e.g., an `is_emergency_active` flag) within the `MQTTService` or a dedicated state service accessible by the API route.
    *   [ ] **Modify:** `mqtt_service._handle_emergency_message` to update the shared emergency state flag.
*   [ ] **Frontend: Polling & State:**
    *   [ ] Implement polling logic in global context provider (`AppProvider`) using `setInterval` calling `GET /api/status/emergency`.
    *   [ ] Store `isEmergencyActive` boolean in context state.
*   [ ] **Frontend: Display:**
    *   [ ] Implement a banner component (e.g., using `shadcn/ui` `Alert` with `variant="destructive"`).
    *   [ ] Conditionally render the banner at the top of the main App layout based on the `isEmergencyActive` state from context.
*   [ ] **Database:** No changes required.

## Milestone 13: Frontend - Styling & Refinement

**Goal:** Apply consistent styling, ensure responsiveness, and improve overall UX.

*   [ ] **Frontend: Styling:**
    *   [ ] Review all components and pages, apply consistent styling using Tailwind utility classes and `shadcn/ui` component variants/props.
    *   [ ] Ensure theme (light/dark if implemented via shadcn) is applied correctly.
*   [ ] **Frontend: Responsiveness:**
    *   [ ] Test application on different screen sizes (desktop, tablet, mobile).
    *   [ ] Adjust layouts (grids, flex properties, table display) as needed using Tailwind's responsive modifiers.
*   [ ] **Frontend: UX Enhancements:**
    *   [ ] Add loading indicators/skeletons (e.g., `shadcn/ui` `Skeleton`) during data fetching.
    *   [ ] Implement consistent error handling display (e.g., using `shadcn/ui` `Toast` for transient errors, `Alert` for page-level errors).
    *   [ ] Review navigation flow and user interactions for clarity.
*   [ ] **Backend API:** No changes required.
*   [ ] **Database:** No changes required.

## (Optional) Milestone 14: Frontend - Dockerization

**Goal:** Containerize the frontend application for deployment.

*   [ ] **Frontend:**
    *   [ ] Create `Dockerfile` in `frontend/` (use multi-stage build: Node stage to build static assets, Nginx/Caddy stage to serve them).
    *   [ ] Add `.dockerignore` file.
*   [ ] **Configuration:**
    *   [ ] Update root `docker-compose.yml` to include/uncomment the `frontend` service definition.
    *   [ ] Configure environment variables for API URL if needed within the container.
*   [ ] **Testing:** Build and run the frontend container locally, ensuring it connects to the API container.

---


**Goal:** Implement the view and functionality to manage employees.

*   [ ] **Backend API:**
    *   [ ] **Implement:** `GET /admin/employees` (list all, paginated?).
    *   [ ] **Implement:** `POST /admin/employees` (create new, handle form data including optional photo upload, trigger embedding generation).
    *   [ ] **Implement:** `GET /admin/employees/<employee_id>` (get single for edit).
    *   [ ] **Implement:** `PUT /admin/employees/<employee_id>` (update, handle photo update/embedding regeneration).
    *   [ ] **Implement:** `DELETE /admin/employees/<employee_id>` (delete).
    *   [ ] **Implement:** New routes in `admin.py` (or a new `employees.py` blueprint) for all CRUD operations.
    *   [ ] **Implement:** New methods in `database.py` for Employee CRUD logic (Create, Read, Update, Delete).
    *   [ ] **Implement:** Logic in Create/Update to handle image storage and trigger embedding via `FaceRecognitionClient`.
*   [ ] **Frontend: Employee Page & Table:**
    *   [ ] Implement `EmployeesPage` component.
    *   [ ] Implement table using `shadcn/ui` `Table` to display employees (fetch from `GET /admin/employees`). Columns: ID, Name, Email, Role, RFID Tag, Photo Thumbnail, Actions (Edit/Delete buttons).
    *   [ ] Add "Create New Employee" button.
*   [ ] **Frontend: Employee Form (Create/Edit):**
    *   [ ] Implement reusable `EmployeeForm` component (likely within a `shadcn/ui` `Dialog` or `Sheet`).
    *   [ ] Include form fields (Name, Email, Role, RFID Tag) using `shadcn/ui` `Input`, `Label`, etc. Add file input for photo.
    *   [ ] Handle form submission for Create (`POST`) and Edit (`PUT`).
*   [ ] **Frontend: Delete Action:**
    *   [ ] Implement `handleDelete` function triggered by delete button in table row.
    *   [ ] Use `shadcn/ui` `AlertDialog` for confirmation before calling `DELETE /admin/employees/<id>`.
    *   [ ] Update table UI on successful deletion.
*   [ ] **Database:** Ensure backend API correctly implements CRUD operations on `employees` table, including handling image storage and embedding logic.

## Milestone 12: Frontend - Emergency Status Display

**Goal:** Implement the real-time display of the system's emergency status.

*   [ ] **Backend API:**
    *   [ ] **Implement:** `GET /api/status/emergency` endpoint. Reads the current emergency state maintained by the API service (updated via MQTT subscriber).
    *   [ ] **Implement:** New route (e.g., in `routes/system.py` or similar) for the status endpoint.
    *   [ ] **Implement:** State management (e.g., an `is_emergency_active` flag) within the `MQTTService` or a dedicated state service accessible by the API route.
    *   [ ] **Modify:** `mqtt_service._handle_emergency_message` to update the shared emergency state flag.
*   [ ] **Frontend: Polling & State:**
    *   [ ] Implement polling logic in global context provider (`AppProvider`) using `setInterval` calling `GET /api/status/emergency`.
    *   [ ] Store `isEmergencyActive` boolean in context state.
*   [ ] **Frontend: Display:**
    *   [ ] Implement a banner component (e.g., using `shadcn/ui` `Alert` with `variant="destructive"`).
    *   [ ] Conditionally render the banner at the top of the main App layout based on the `isEmergencyActive` state from context.
*   [ ] **Database:** No changes required.

## Milestone 13: Frontend - Styling & Refinement

**Goal:** Apply consistent styling, ensure responsiveness, and improve overall UX.

*   [ ] **Frontend: Styling:**
    *   [ ] Review all components and pages, apply consistent styling using Tailwind utility classes and `shadcn/ui` component variants/props.
    *   [ ] Ensure theme (light/dark if implemented via shadcn) is applied correctly.
*   [ ] **Frontend: Responsiveness:**
    *   [ ] Test application on different screen sizes (desktop, tablet, mobile).
    *   [ ] Adjust layouts (grids, flex properties, table display) as needed using Tailwind's responsive modifiers.
*   [ ] **Frontend: UX Enhancements:**
    *   [ ] Add loading indicators/skeletons (e.g., `shadcn/ui` `Skeleton`) during data fetching.
    *   [ ] Implement consistent error handling display (e.g., using `shadcn/ui` `Toast` for transient errors, `Alert` for page-level errors).
    *   [ ] Review navigation flow and user interactions for clarity.
*   [ ] **Backend API:** No changes required.
*   [ ] **Database:** No changes required.

## (Optional) Milestone 14: Frontend - Dockerization

**Goal:** Containerize the frontend application for deployment.

*   [ ] **Frontend:**
    *   [ ] Create `Dockerfile` in `frontend/` (use multi-stage build: Node stage to build static assets, Nginx/Caddy stage to serve them).
    *   [ ] Add `.dockerignore` file.
*   [ ] **Configuration:**
    *   [ ] Update root `docker-compose.yml` to include/uncomment the `frontend` service definition.
    *   [ ] Configure environment variables for API URL if needed within the container.
*   [ ] **Testing:** Build and run the frontend container locally, ensuring it connects to the API container.

---

