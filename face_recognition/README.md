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
*   (Deletion) Entire `face_recognition/` directory (after successful migration)

**Migration Steps & TODOs:**

1.  **[X] Set Up DeepFace Docker Service:**
    *   **Target File:** `docker-compose.yml` (Main project compose file)
    *   **Subtasks:**
        *   [X] Remove the existing `face_recognition` service definition.
        *   [X] Add a new service definition named `deepface` using a suitable image (e.g., `serengil/deepface`).
        *   [X] Map ports correctly (e.g., map DeepFace internal port 5000 to external port 5001: `- "5001:5000"`).
        *   [X] Add the `deepface` service to the `cses_network`.
        *   [X] **(Critical Research):** Determine how to configure the DeepFace container to use **GhostFaceNet** as the model for API calls (`/represent`, `/verify`). This might involve environment variables (`-e DEEPFACE_DEFAULT_MODEL=GhostFaceNet`?) or command overrides. Consult DeepFace documentation.
        *   [X] Test basic container startup: `docker-compose up deepface`.

2.  **[X] Update API Configuration:**
    *   **Target Files:**  `api/config.py`
    *   **Subtasks:**
        *   [X] Change the `FACE_RECOGNITION_URL` variable to point to the new service (e.g., `http://deepface:5000` using Docker network name and internal port).

3.  **[ ] Refactor API's Face Recognition Client:**
    *   **Target File:** `api/services/face_recognition_client.py`
    *   **Subtasks:**
        *   [ ] **Embedding:** Modify the `get_embedding` method:
            *   [ ] Change endpoint URL from `/embed` to DeepFace's `/represent`.
            *   [ ] Update the request payload structure. Send image base64 (check expected key, e.g., `img_path`). Crucially, include parameters to specify `model_name="GhostFaceNet"`.
            *   [ ] Update the response parsing logic to extract the embedding vector from DeepFace's JSON structure (e.g., `response.json()['results'][0]['embedding']` - *verify exact structure*).
        *   [ ] **Verification:** Modify the `verify_embeddings` method (potentially rename to `verify_images`):
            *   [ ] Change endpoint URL from `/verify` to DeepFace's `/verify`.
            *   [ ] Update the request payload structure. Send a list containing *two* image representations (e.g., base64 strings), specify `model_name="GhostFaceNet"`, and potentially `detector_backend`.
            *   [ ] Update response parsing logic to extract `verified` (boolean) and `distance`/`similarity` from DeepFace's JSON structure.
        *   [ ] **Health Check:** Update `check_health` to call DeepFace's root `/` or other health endpoint if available.

4.  **[ ] Adapt API Logic (MQTT Service):**
    *   **Target File:** `api/services/mqtt_service.py` (`_handle_session_message` function)
    *   **Subtasks (Choose one verification approach):**
        *   **Approach A (DeepFace handles verification):**
            *   [ ] Modify the flow to call the *new* `face_client.verify_images` method.
            *   [ ] **(Major Dependency):** Implement logic to get the **reference employee image data** (as base64). Currently, only the URL is stored. This requires either:
                *   Fetching the image from the static URL (adds HTTP request).
                *   Changing the DB schema/data loading to store image blobs or base64 directly for employees.
            *   [ ] Pass both the incoming image base64 and the reference image base64 to `face_client.verify_images`.
            *   [ ] Use the boolean result directly from DeepFace. Confidence might be derived from distance/threshold in the response.
        *   **Approach B (API compares embeddings):**
            *   [ ] Keep the existing logic structure (get embedding 1, get embedding 2, compare).
            *   [ ] Ensure `face_client.get_embedding` (now calling `/represent`) is used for both incoming and reference embeddings.
            *   [ ] **(Major Dependency):** Still need reference employee embedding. This means ensuring `employees.face_embedding` is populated using the *DeepFace* `/represent` endpoint (requires re-running embedding generation for sample data *after* setting up DeepFace).
            *   [ ] Perform cosine similarity calculation within the API service as currently done (but using DeepFace embeddings).

5.  **[ ] Regenerate Sample Data Embeddings:**
    *   **Target Script:** `face_recognition/tests/generate_embeddings_for_sample_data.py` (or equivalent)
    *   **Subtasks:**
        *   [ ] Once the `deepface` container is running and configured for GhostFaceNet, run this script (it already calls the configured URL) to populate `database/sample_data.sql` with embeddings generated by DeepFace/GhostFaceNet.

6.  **[ ] Testing:**
    *   [ ] Test the API `/embed` equivalent via the client.
    *   [ ] Test the API `/verify` equivalent via the client.
    *   [ ] Perform end-to-end testing by sending MQTT messages and verifying database logs and notifications.

7.  **[ ] Cleanup:**
    *   [ ] Once migration is successful and tested, delete the entire `face_recognition/` directory.
    *   [ ] Remove old dependencies from the API's `requirements.txt` if they are no longer needed (e.g., `tensorflow` if it was only for the custom service).

---
*Previous TODOs for custom pipeline (Normalization, Alignment, Threshold) are now superseded by this migration plan.*



