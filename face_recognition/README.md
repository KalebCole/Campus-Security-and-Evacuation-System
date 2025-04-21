# Face Recognition Module

This module provides face recognition functionality for the Campus Security and Evacuation System.

## Structure

The face recognition module is organized into the following components:

- **core/**: Contains the core face recognition functionality
  - `preprocessing.py`: Image preprocessing utilities
  - `embedding.py`: Face embedding generation
  - `verification.py`: Face matching and verification
  - `models/`: Directory for model files (you need to add your GhostFaceNets model here)

- **service/**: Microservice implementation
  - `app.py`: Flask application setup
  - `routes.py`: API endpoints
  - `Dockerfile`: Container definition
  - `requirements.txt`: Service-specific dependencies

- **config/**: Configuration files
  - `model_config.py`: ML model configuration
  - `paths.py`: File path configurations

- **tests/**: Testing suite
  - `test_pipeline.py`: Integration tests
  - `test_preprocessing.py`: Unit tests
  - `test_images/`: Test image resources

## Setup

### Model Files

Before running the service, you need to download the GhostFaceNets model. The implementation is based on: 
https://github.com/HamadYA/GhostFaceNets

Place the model file in the `core/models/` directory:

```
face_recognition/core/models/ghostfacenets.h5
```

### Running the Service

You can run the face recognition service using Docker:

```bash
cd server/face_recognition
docker-compose up -d
```

Or directly using Python:

```bash
cd server
python -m face_recognition.service.app
```

## API Endpoints

The face recognition service exposes the following endpoints:

- **GET /health**: Health check endpoint
- **POST /embed**: Generate face embedding from an image
- **POST /verify**: Verify if two embeddings match

## Dependencies

The face recognition module requires:

- TensorFlow 2.x
- OpenCV
- NumPy
- Flask (for the service)
- Gunicorn (for production deployment) 


## MILESTONES and TODOs

---
## MILESTONE: Migrate to DeepFace Service

**Goal:** Replace the custom face recognition pipeline (detection, alignment, embedding) with the pre-built DeepFace library, running as a separate Docker service. This aims to simplify maintenance and potentially leverage more robust detection/alignment models included with DeepFace.

**Affected Components:**
*   `docker-compose.yml` (Root or `api/`)
*   `api/config.py`
*   `api/services/face_recognition_client.py`
*   `api/services/mqtt_service.py`
*   `database/init.sql` (Schema change)
*   `database/sample_data.sql` (Data change)
*   `api/models/employee.py` (Model change)
*   `api/routes/admin.py` (Admin UI backend)
*   `api/templates/admin/review_details.html` (Admin UI frontend)
*   (Deletion) Entire `face_recognition/` directory (after successful migration)

**Migration Steps & TODOs:**

1.  **[ ] Set Up DeepFace Docker Service:**
    *   **Target File:** `docker-compose.yml` (Main project compose file)
    *   **Subtasks:**
        *   [X] Remove the existing `face_recognition` service definition. *(Effectively done by using deepface service)*
        *   [X] Add a new service definition named `deepface` using `serengil/deepface`. *(Done)*
        *   [X] Map ports correctly (`- "5001:5000"`). *(Done)*
        *   [X] Add the `deepface` service to the `cses_network`. *(Done)*
        *   [X] **(Critical Research):** Confirm how to configure the DeepFace container for **GhostFaceNet** (environment variables or command overrides?), OR confirm specifying in API calls is sufficient. *(Assuming API call parameter is sufficient for now)*.
        *   [X] Test basic container startup: `docker-compose up deepface`. *(Confirmed working)*

2.  **[X] Update API Configuration:**
    *   **Target Files:** `api/config.py`
    *   **Subtasks:**
        *   [X] Change the `FACE_RECOGNITION_URL` variable default to `http://deepface:5000`. *(Done)*

3.  **[ ] Refactor API's Face Recognition Client:**
    *   **Target File:** `api/services/face_recognition_client.py`
    *   **Subtasks:**
        *   [X] **Embedding:** Modify `get_embedding` for DeepFace `/represent`. *(Done)*
        *   [ ] **Verification:** Modify `verify_embeddings` method (rename to `verify_images`): 
            *   [ ] Change implementation to call DeepFace's `/verify` endpoint.
            *   [ ] Update the request payload structure (send list of two base64 images, `model_name="GhostFaceNet"`).
            *   [ ] Update response parsing logic for `verified`, `distance`, etc.
        *   [X] **Health Check:** Update `check_health` for DeepFace root endpoint. *(Done)*

4.  **[ ] Modify Database for Reference Images:**
    *   **Target Files:** `database/init.sql`, `api/models/employee.py`, `database/sample_data.sql`
    *   **Subtasks:**
        *   [ ] In `init.sql`, change the `employees` table: rename `photo_url VARCHAR` to `photo_base64 TEXT` (or similar).
        *   [ ] In `api/models/employee.py`, update the `Employee` SQLAlchemy model to reflect the column name change.
        *   [ ] In `sample_data.sql`, update the `INSERT INTO employees` statements: remove the old URL paths and replace them with actual base64 encoded strings for each employee's reference photo. *(Requires generating these base64 strings)*.
        *   [ ] Update any other scripts/code that might interact directly with `employee.photo_url`. 

5.  **[X] Adapt API Logic (MQTT Service - Use DeepFace Verify):**
    *   **Target File:** `api/services/mqtt_service.py` (`_handle_session_message` function)
    *   **Subtasks:**
        *   [X] Modify the flow to call the new `face_client.verify_images` method.
        *   [X] Implement logic to fetch the `employee.photo_base64` string from the database for the matched RFID tag.
        *   [X] Pass both the incoming image base64 and the fetched reference image base64 to `face_client.verify_images`.
        *   [ ] Use the boolean result (`verified`) and potentially `distance`/`threshold` from the DeepFace response to determine `access_granted` and `confidence`.
        *   [ ] Remove the local cosine similarity calculation logic previously added to `face_client.py` (or comment it out if `verify_images` replaces `verify_embeddings`).

6.  **[ ] Update Admin Review UI for Base64:**
    *   **Target Files:** `api/routes/admin.py` (likely the route fetching review details), `api/templates/admin/review_details.html`
    *   **Subtasks:**
        *   [ ] In the relevant `admin.py` route, when fetching employee details for review, retrieve the `photo_base64` string.
        *   [ ] Construct a Data URI string (e.g., `f"data:image/jpeg;base64,{employee.photo_base64}"`) from the base64 data.
        *   [ ] Pass this Data URI to the `review_details.html` template.
        *   [ ] Ensure the `<img>` tag in the template uses the Data URI variable for its `src` attribute to display the reference photo.

7.  **[ ] Regenerate Sample Data Embeddings (If Still Needed):**
    *   **Target Script:** `face_recognition/tests/generate_embeddings_for_sample_data.py` (or equivalent)
    *   **Subtasks:**
        *   [ ] If verification *still* relies on comparing embeddings stored in `employees.face_embedding` (e.g., if `/verify` isn't used), run the script to populate `sample_data.sql` with embeddings generated via DeepFace `/represent`.

8.  **[ ] Testing:**
    *   [ ] Test the `/represent` endpoint via the client.
    *   [ ] Test the `/verify` endpoint via the client.
    *   [ ] Test the Admin Review UI reference photo display.
    *   [ ] Perform end-to-end testing by sending MQTT messages and verifying database logs and notifications.

9.  **[ ] Cleanup:**
    *   [ ] Once migration is successful and tested, delete the entire `face_recognition/` directory.
    *   [ ] Remove old dependencies from the API's `requirements.txt` if no longer needed.

---
*Previous TODOs for custom pipeline are now superseded by this migration plan.*



