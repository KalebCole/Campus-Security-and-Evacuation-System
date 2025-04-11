"""Integration tests for the Campus Security Enhancement System API."""

import json
import base64
import time
from pathlib import Path
import paho.mqtt.client as mqtt
import os
import pytest
import numpy as np
import logging
import requests
import psycopg2

# Set up logging for the test
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def verify_face_recognition_service():
    """Verify that face recognition service is running and accessible"""
    url = os.getenv('FACE_RECOGNITION_URL', 'http://localhost:5001')
    try:
        response = requests.get(f"{url}/health")
        if response.status_code == 200:
            logger.info(f"Face recognition service is up at {url}")
            return True
        else:
            logger.error(
                f"Face recognition service returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Could not connect to face recognition service: {e}")
        return False


def test_mqtt_session_with_face_recognition(client):
    """
    Test the full flow of receiving a session via MQTT and processing it with face recognition.

    Requirements:
    - MQTT broker running (mosquitto)
    - Face recognition service running
    - Test image in tests/test_images/kaleb.jpeg
    """
    # First verify face recognition service is available
    if not verify_face_recognition_service():
        pytest.skip("Face recognition service is not available")

    # Load test image
    image_path = Path(__file__).parent / "test_images" / "kaleb.jpeg"
    logger.info(f"Using test image from {image_path}")

    if not image_path.exists():
        pytest.fail(f"Test image not found at {image_path}")

    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode()
        logger.debug(
            f"Successfully loaded and encoded test image (length: {len(image_data)})")

    # Create test session
    session = {
        "session_id": "test_session_123",
        "face_data": image_data,
        "rfid_data": "test_rfid_456",
        "timestamp": "2024-03-19T12:00:00Z"
    }

    # Message delivery confirmation
    message_delivered = False

    def on_publish(client, userdata, mid):
        nonlocal message_delivered
        logger.debug("Message delivered successfully")
        message_delivered = True

    # Connect to MQTT broker with clean session and client ID
    mqtt_client = mqtt.Client(client_id="test_client", clean_session=True)
    mqtt_client.on_publish = on_publish

    try:
        mqtt_client.connect(
            host=os.getenv('MQTT_BROKER_ADDRESS', 'localhost'),
            port=int(os.getenv('MQTT_BROKER_PORT', 1883))
        )

        # Start the MQTT loop
        mqtt_client.loop_start()
        logger.debug("Starting MQTT loop")

        # Create a clean version of the session for logging
        debug_session = session.copy()
        debug_session['face_data'] = '<base64_image_data>'
        logger.debug(f"Publishing session: {debug_session}")

        # Publish session message with QoS 1
        mqtt_client.publish("campus/security/session",
                            json.dumps(session), qos=1)

        # Wait for message delivery confirmation
        delivery_timeout = 2  # seconds
        delivery_start = time.time()
        while not message_delivered and time.time() - delivery_start < delivery_timeout:
            time.sleep(0.1)

        if not message_delivered:
            pytest.fail("Message delivery confirmation not received")

        logger.debug("Message confirmed delivered, waiting for processing")

    except Exception as e:
        pytest.fail(f"Failed to connect to MQTT broker: {str(e)}")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.debug("MQTT client disconnected")

    # Wait for processing (adjust timeout as needed)
    max_wait = 10  # Increased timeout for processing
    start_time = time.time()
    processed = False
    test_session = None

    while time.time() - start_time < max_wait:
        # Check sessions endpoint
        response = client.get('/api/sessions')
        assert response.status_code == 200, "Failed to get sessions"
        sessions = response.get_json()

        # Clean sessions for logging
        debug_sessions = []
        for s in sessions:
            s_clean = s.copy()
            if 'face_data' in s_clean:
                s_clean['face_data'] = '<base64_image_data>'
            if 'embedding' in s_clean:
                s_clean['embedding'] = f'<embedding_array_length_{len(s["embedding"])}>'
            debug_sessions.append(s_clean)
        logger.debug(f"Current sessions: {debug_sessions}")

        # Look for our test session
        for sess in sessions:
            if sess['session_id'] == session['session_id']:
                status_msg = f"Found session {sess['session_id']} with status {sess['status']}"
                if 'embedding' in sess:
                    status_msg += f" (embedding length: {len(sess['embedding'])})"
                logger.debug(status_msg)

                if sess['status'] == 'processed':
                    processed = True
                    test_session = sess
                    break
                elif sess['status'] == 'error':
                    logger.error(
                        f"Session failed with error: {sess.get('error', 'No error message')}")
                    pytest.fail(
                        f"Session processing failed: {sess.get('error', 'No error message')}")

        if processed:
            break
        time.sleep(0.5)

    # Basic session processing assertions
    assert processed, "Session was not processed within timeout"
    assert test_session is not None, "Test session not found"
    assert test_session['status'] == 'processed'
    assert test_session['rfid_data'] == session['rfid_data']

    # Embedding specific assertions
    assert 'embedding' in test_session, "No embedding generated"
    embedding = test_session['embedding']
    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) > 0, "Embedding should not be empty"

    # Convert to numpy array to check properties
    embedding_array = np.array(embedding)
    assert embedding_array.ndim == 1, "Embedding should be 1-dimensional"
    assert not np.isnan(embedding_array).any(), "Embedding contains NaN values"
    assert not np.isinf(embedding_array).any(
    ), "Embedding contains infinite values"


def test_vector_similarity_search(client):
    """
    Test vector similarity search functionality using face embeddings.

    Requirements:
    - Face recognition service running
    - PostgreSQL database running
    - Test image in tests/test_images/kaleb.jpeg
    """
    # First verify face recognition service is available
    if not verify_face_recognition_service():
        pytest.skip("Face recognition service is not available")

    # Load test image
    image_path = Path(__file__).parent / "test_images" / "kaleb.jpeg"
    logger.info(f"Using test image from {image_path}")

    if not image_path.exists():
        pytest.fail(f"Test image not found at {image_path}")

    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode()
        logger.debug(
            f"Successfully loaded and encoded test image (length: {len(image_data)})")

    # Create test session to get embedding
    session = {
        "session_id": "test_vector_search_123",
        "face_data": image_data,
        "rfid_data": "test_vector_456",
        "timestamp": "2024-03-19T12:00:00Z"
    }

    # Get embedding through API
    response = client.post('/api/process_image', json=session)
    assert response.status_code == 200, "Failed to process image"
    result = response.get_json()
    assert 'embedding' in result, "No embedding in response"

    # Get the embedding and convert to numpy array
    embedding = np.array(result['embedding'])
    assert embedding.ndim == 1, "Embedding should be 1-dimensional"
    assert not np.isnan(embedding).any(), "Embedding contains NaN values"
    assert not np.isinf(embedding).any(), "Embedding contains infinite values"

    # Connect to database and perform vector search testing
    with psycopg2.connect(
        dbname="cses_db",
        user="cses_admin",
        password="cses_password_123!",
        host="localhost",
        port=5432
    ) as conn:
        with conn.cursor() as cur:
            # Store the original embedding
            cur.execute("""
                INSERT INTO employees (name, rfid_tag, role, email, face_embedding)
                VALUES ('Test Original', %s, 'Security Officer', 'test.original@acme.local', %s::vector)
                RETURNING id
            """, (session['rfid_data'], embedding.tolist()))
            original_id = cur.fetchone()[0]

            # Create and store variations of the embedding
            similar_embedding = embedding * 0.95  # 95% similar
            different_embedding = embedding * -0.5  # Very different

            cur.execute("""
                INSERT INTO employees (name, rfid_tag, role, email, face_embedding)
                VALUES 
                    ('Test Similar', 'TEST_SIM_001', 'Security Officer', 'test.similar@acme.local', %s::vector),
                    ('Test Different', 'TEST_DIFF_001', 'Security Officer', 'test.different@acme.local', %s::vector)
            """, (similar_embedding.tolist(), different_embedding.tolist()))

            # Perform vector similarity search
            cur.execute("""
                SELECT 
                    name, 
                    face_embedding <=> %s::vector as distance
                FROM employees
                WHERE face_embedding IS NOT NULL
                ORDER BY face_embedding <=> %s::vector
                LIMIT 3
            """, (embedding.tolist(), embedding.tolist()))

            results = cur.fetchall()

            # Log results for debugging
            logger.debug("Vector search results:")
            for name, distance in results:
                logger.debug(f"- {name}: distance = {distance}")

            # Validate search results
            assert len(results) == 3, "Should find 3 similar faces"

            # First result should be the exact match
            assert results[0][0] == 'Test Original', "First result should be the original face"
            assert results[0][
                1] < 0.1, f"Distance to self should be very small (got {results[0][1]})"

            # Second result should be the similar embedding
            assert results[1][0] == 'Test Similar', "Second result should be the similar face"
            assert 0.1 < results[1][
                1] < 0.5, f"Distance to similar face should be moderate (got {results[1][1]})"

            # Third result should be the different embedding
            assert results[2][0] == 'Test Different', "Third result should be the different face"
            assert results[2][
                1] > 0.5, f"Distance to different face should be large (got {results[2][1]})"

            # Cleanup test data
            cur.execute("""
                DELETE FROM employees 
                WHERE rfid_tag IN (%s, 'TEST_SIM_001', 'TEST_DIFF_001')
            """, (session['rfid_data'],))


