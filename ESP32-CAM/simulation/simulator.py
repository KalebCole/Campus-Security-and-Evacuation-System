import cv2
import numpy as np
import paho.mqtt.client as mqtt
import time
import base64
import json
import os
import argparse
from datetime import datetime

# Parse command-line arguments
parser = argparse.ArgumentParser(description='ESP32-CAM Simulator')
parser.add_argument('--broker', default='localhost',
                    help='MQTT broker address')
parser.add_argument('--port', type=int, default=1883, help='MQTT broker port')
parser.add_argument('--topic', default='campus/security/face',
                    help='MQTT topic for face images')
parser.add_argument('--image-dir', default='./test_images',
                    help='Directory with test face images')
parser.add_argument('--confidence', type=float, default=0.5,
                    help='Minimum confidence threshold for face detection')
parser.add_argument('--nms-threshold', type=float, default=0.3,
                    help='Non-Maximum Suppression threshold')
args = parser.parse_args()

# Create MQTT client
client = mqtt.Client()

# Connect to MQTT broker
print(f'Connecting to MQTT broker at {args.broker}:{args.port}')
client.connect(args.broker, args.port, 60)
client.loop_start()


def load_test_images(directory):
    """Load all images from a directory"""
    images = []
    if directory and os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                path = os.path.join(directory, filename)
                img = cv2.imread(path)
                if img is not None:
                    images.append((filename, img))

    # If no images found, create a test pattern
    if not images:
        img = np.zeros((320, 240, 3), dtype=np.uint8)
        cv2.putText(img, 'ESP32-CAM Simulator', (30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        images.append(('test_pattern.jpg', img))

    return images


def non_max_suppression(boxes, scores, threshold):
    """Apply Non-Maximum Suppression to filter overlapping detections"""
    if len(boxes) == 0:
        return []

    # Sort boxes by confidence score
    indices = np.argsort(scores)[::-1]
    keep = []

    while len(indices) > 0:
        # Get the box with highest score
        current = indices[0]
        keep.append(current)

        if len(indices) == 1:
            break

        # Get IoU of current box with all other boxes
        current_box = boxes[current]
        other_boxes = boxes[indices[1:]]

        # Calculate IoU
        x1 = np.maximum(current_box[0], other_boxes[:, 0])
        y1 = np.maximum(current_box[1], other_boxes[:, 1])
        x2 = np.minimum(current_box[0] + current_box[2],
                        other_boxes[:, 0] + other_boxes[:, 2])
        y2 = np.minimum(current_box[1] + current_box[3],
                        other_boxes[:, 1] + other_boxes[:, 3])

        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        current_area = current_box[2] * current_box[3]
        other_areas = other_boxes[:, 2] * other_boxes[:, 3]
        union = current_area + other_areas - intersection

        iou = intersection / union

        # Remove boxes with IoU > threshold
        indices = indices[1:][iou <= threshold]

    return keep


def simulate_face_detection(image):
    """Simulate ESP-WHO face detection with improved filtering"""
    # Step 1: Resize to ESP32-CAM resolution (320x240)
    height, width = image.shape[:2]
    if height > 240 or width > 320:
        scale = min(320/width, 240/height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = cv2.resize(image, (new_width, new_height))

    # Step 2: Convert to grayscale (ESP-WHO works with grayscale)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Step 3: Apply histogram equalization (like ESP-WHO)
    gray = cv2.equalizeHist(gray)

    # Step 4: Detect faces with stricter parameters
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # ESP-WHO-like parameters:
    # - scaleFactor: 1.1 (smaller steps for better detection)
    # - minNeighbors: 5 (more strict, requires more neighbors)
    # - minSize: (30, 30) (minimum face size)
    # - maxSize: (200, 200) (maximum face size)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
        maxSize=(200, 200),
        flags=cv2.CASCADE_SCALE_IMAGE
    )

    if len(faces) == 0:
        return image, []

    # Step 5: Apply NMS with stricter threshold
    boxes = faces
    scores = np.ones(len(faces))
    keep = non_max_suppression(
        boxes, scores, threshold=0.4)  # More aggressive NMS
    filtered_faces = faces[keep]

    # Step 6: Process each face
    detected_faces = []
    for (x, y, w, h) in filtered_faces:
        # Draw rectangle and label
        cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(image, f'Face', (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Extract face region
        face = image[y:y+h, x:x+w]

        # Step 7: Resize to MobileFaceNet input size (112x112)
        if face.size > 0:
            face_resized = cv2.resize(face, (112, 112))
            detected_faces.append(face_resized)

    return image, detected_faces


def publish_face(face_img, device_id='simulator'):
    """Publish a face image to MQTT"""
    try:
        # Encode the image
        _, img_encoded = cv2.imencode('.jpg', face_img)
        img_bytes = img_encoded.tobytes()

        # Encode as base64 for MQTT transmission
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Create message payload
        payload = {
            'device_id': device_id,
            'timestamp': datetime.now().isoformat(),
            'image': img_base64,
            'format': 'jpg'
        }

        # Publish to MQTT topic
        topic = f'{args.topic}/{device_id}'
        print(f'Publishing face image to {topic}')
        client.publish(topic, json.dumps(payload))
        return True
    except Exception as e:
        print(f'Error publishing face: {e}')
        return False


def main():
    print('ESP32-CAM Simulator starting...')
    print(f'MQTT Topic: {args.topic}')
    print('Loading test images...')

    # Check for test images directory, use server test images if not available
    if not os.path.exists(args.image_dir):
        server_test_images = 'server/api_tests/test_images'
        if os.path.exists(server_test_images):
            args.image_dir = server_test_images
            print(f'Using test images from {args.image_dir}')
        else:
            print('No test images found. Using a generated test pattern.')
            args.image_dir = None

    # Load test images
    test_images = load_test_images(args.image_dir)
    print(f'Loaded {len(test_images)} test images')

    # Main simulation loop
    try:
        while True:
            for name, img in test_images:
                print(f'Processing image: {name}')

                # Display original image
                cv2.imshow('ESP32-CAM Simulator - Original', img)

                # Detect faces
                display_img, faces = simulate_face_detection(img.copy())

                # Display detection results
                cv2.imshow('ESP32-CAM Simulator - Detection', display_img)

                # If faces detected, publish them
                if faces:
                    print(f'Detected {len(faces)} faces')
                    for i, face in enumerate(faces):
                        cv2.imshow(f'Face {i+1}', face)
                        publish_face(face)
                else:
                    print('No faces detected')

                # Wait for key press or 5 seconds
                key = cv2.waitKey(5000)
                if key == 27:  # ESC key
                    raise KeyboardInterrupt

            print('Completed one cycle of test images')
    except KeyboardInterrupt:
        print('Simulation stopped by user')
    finally:
        # Clean up
        cv2.destroyAllWindows()
        client.loop_stop()
        client.disconnect()
        print('ESP32-CAM Simulator stopped')


if __name__ == '__main__':
    main()
