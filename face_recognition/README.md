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

[ ] **Preprocessing Normalization Correction:**  
    - [ ] In `core/preprocessing.py`, replace the current normalization line:  
      ```
      # Old (incorrect)
      resized = (resized - 127.5) / 128.0
      # New (correct)
      resized = resized.astype(np.float32) / 255.0
      ```
    - [ ] Update or add tests in `tests/test_preprocessing.py` to validate that pixel values are in the `[0, 1]` range after preprocessing.

- [ ] **Enable Embedding L2 Normalization:**  
    - [ ] In `core/embedding.py`, uncomment and ensure the following line is present after model prediction:  
      ```
      embedding = embedding / (np.linalg.norm(embedding) + 1e-10)
      ```
    - [ ] Add or update tests in `tests/test_pipeline.py` to confirm all output embeddings are unit-normalized.

- [ ] **Add Diagnostic Similarity Tests:**  
    - [ ] Implement a self-similarity test (identical images should yield a similarity score close to 1.0).
    - [ ] Implement a cross-similarity test (different people should yield a similarity score significantly lower, e.g., <0.3).
    - [ ] Use these tests to validate the effectiveness of normalization and thresholding changes.

- [ ] **Model Architecture Verification:**  
    - [ ] Confirm the loaded `.h5` file matches the expected GhostFaceNet architecture (input size, output dimension).
    - [ ] Check that the input layer expects 112x112 RGB images and the output is a 512-D vector.

- [ ] **Investigate Embedding Normalization:** Evaluate removing redundant L2 normalization post-model prediction.
    - [ ] In `core/embedding.py`, comment out/remove the line `embedding = embedding / np.linalg.norm(embedding)`.
    - [ ] Verify that `generate_embedding` still produces embeddings of the expected shape (e.g., 512 dimensions).
    - [ ] *Dependency: Link to Threshold Tuning* - Set up a basic test to compare a few known matching/non-matching face pairs using cosine similarity with both the original and the modified embedding generation. Note preliminary observations on score separation.

- [ ] **Implement Face Detection & Alignment:** Enhance preprocessing to ensure consistent face input to the model.
    - [ ] **Choose Face Detector:** Decide on a face detection library/model (e.g., OpenCV DNN, MTCNN, RetinaFace). Consider dependency management. *Initial Choice Suggestion: OpenCV DNN module due to likely existing `cv2` dependency.*
    - [ ] **Load Detector Model:** Add code to load the chosen pre-trained face detection model weights in `core/preprocessing.py` or a related utility function.
    - [ ] **Implement Detection Logic:** Create a function that takes the raw input image (`np.ndarray`) and returns the bounding box of the most prominent face (or handles no/multiple faces).
    - [ ] **Choose Alignment Strategy:**
        - [ ] *Subtask (Option A - Simpler):* Implement cropping based on the detected bounding box (potentially with added margin/aspect ratio handling).
        - [ ] *Subtask (Option B - Better but Complex):* Research and integrate a facial landmark detector. Implement affine transformation based on landmarks (e.g., aligning eyes horizontally) before cropping.
    - [ ] **Integrate into Pipeline:** Modify the process so that the detected/cropped/aligned face is passed to the existing `preprocess_image` function (which handles resize/pixel normalization). Ensure the original `preprocess_image` is called with the *output* of the detection/alignment step.
    - [ ] **Test Preprocessing:** Test the new detection/alignment/preprocessing flow with various images (different sizes, lighting, face angles) to ensure robustness.

- [ ] **Evaluate and Tune Verification Threshold:** Determine the optimal cosine similarity threshold for matching.
    - [ ] **Create Test Set:** Gather a small, labeled dataset of face images (e.g., 5-10 images each of 5-10 distinct individuals).
    - [ ] **Generate Test Embeddings:** Using the *finalized* embedding generation pipeline (after addressing normalization/alignment), generate and store embeddings for all images in the test set.
    - [ ] **Calculate Similarity Scores:**
        - [ ] Compute all intra-class similarity scores (comparisons between different images of the *same* person).
        - [ ] Compute a representative sample of inter-class similarity scores (comparisons between images of *different* people).
    - [ ] **Analyze Score Distributions:** Examine the range, mean, and standard deviation of both intra-class and inter-class scores. Plotting histograms can be very helpful.
    - [ ] **Determine Optimal Threshold:** Choose a threshold value that provides the best balance between minimizing False Accept Rate (FAR) and False Reject Rate (FRR) for your requirements. Visualize this on the score distributions.
    - [ ] **Update Verifier:** Update the default `threshold` value in the `FaceVerifier` class within `core/verification.py`. Consider making it configurable (e.g., via environment variable or config file) if needed for different deployment scenarios.



