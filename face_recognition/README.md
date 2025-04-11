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