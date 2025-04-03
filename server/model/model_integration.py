import os
import sys
# Add server directory to path for imports
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)
from app_config import Config
import logging


if not Config.MOCK_VALUE:
    from tensorflow.keras.models import Model, Sequential
    from tensorflow.keras.layers import Input, Convolution2D, ZeroPadding2D, MaxPooling2D, Flatten, Dense, Dropout, Activation
    from PIL import Image
    from tensorflow.keras.preprocessing.image import load_img, save_img, img_to_array
    from tensorflow.keras.applications.imagenet_utils import preprocess_input
    from tensorflow.keras.preprocessing import image
    import tensorflow as tf
    import cv2
    import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_embedding(image_input):
    """Main function to generate embeddings from image input"""
    if Config.MOCK_VALUE:
        return [0.1] * 2622
    else:
        return real_generate_embedding(image_input)


def perform_recognition(filename1, filename2):
    """Main function to perform face recognition"""
    if Config.MOCK_VALUE:
        return True  # Mock success
    else:
        return real_perform_recognition(filename1, filename2)


if not Config.MOCK_VALUE:

    def model_load():
        model = Sequential()
        model.add(ZeroPadding2D((1, 1), input_shape=(224, 224, 3)))
        model.add(Convolution2D(64, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(64, (3, 3), activation='relu'))
        model.add(MaxPooling2D((2, 2), strides=(2, 2)))

        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(128, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(128, (3, 3), activation='relu'))
        model.add(MaxPooling2D((2, 2), strides=(2, 2)))

        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(256, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(256, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(256, (3, 3), activation='relu'))
        model.add(MaxPooling2D((2, 2), strides=(2, 2)))

        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(512, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(512, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(512, (3, 3), activation='relu'))
        model.add(MaxPooling2D((2, 2), strides=(2, 2)))

        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(512, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(512, (3, 3), activation='relu'))
        model.add(ZeroPadding2D((1, 1)))
        model.add(Convolution2D(512, (3, 3), activation='relu'))
        model.add(MaxPooling2D((2, 2), strides=(2, 2)))

        model.add(Convolution2D(4096, (7, 7), activation='relu'))
        model.add(Dropout(0.5))
        model.add(Convolution2D(4096, (1, 1), activation='relu'))
        model.add(Dropout(0.5))
        model.add(Convolution2D(2622, (1, 1)))
        model.add(Flatten())
        model.add(Activation('softmax'))

        scripts_path = os.path.dirname(os.path.abspath(__file__))
        weights_path = os.path.join(scripts_path, 'FR_model_weights.h5')
        model.load_weights(weights_path)
        return model

    model = model_load()

    def model_extraction_load():
        get_facial_features = Model(
            inputs=model.layers[0].input, outputs=model.layers[-2].output)
        return get_facial_features

    def haarCascade_load():
        face_cascade = cv2.CascadeClassifier(cv2.samples.findFile(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'))
        return face_cascade

    face_cascade = haarCascade_load()
    facial_features = model_extraction_load()

    def preprocess_image(image_input):
        if isinstance(image_input, str):  # If the input is a file path
            img = load_img(image_input, target_size=(224, 224))
            img = img_to_array(img)
        elif isinstance(image_input, np.ndarray):  # If the input is an array
            # Resize the array to 224x224
            img = cv2.resize(image_input, (224, 224))
        else:
            raise TypeError("Input should be a file path or a numpy array.")

        img = np.expand_dims(img, axis=0)
        img = preprocess_input(img)
        return img

    def real_generate_embedding(image_input):
        embeddings = facial_features.predict(
            preprocess_image(image_input))[0, :]
        return embeddings

    def crop_faces(image, faces):
        cropped_faces = []
        for (x, y, w, h) in faces:
            cropped_face = image[y:y+h, x:x+w]
            cropped_faces.append(cropped_face)
        return cropped_faces

    def verify_face(face1, face2):
        # Generate embeddings for both face arrays
        face1_embedding = generate_embedding(face1)
        face2_embedding = generate_embedding(face2)
        print(f"Embeddings for Image 1: {face1_embedding}")
        print(f"Embeddings for Image 2: {face2_embedding}")

        # Compute cosine similarity
        cosine_similarity = cosineDistance(face1_embedding, face2_embedding)

        # Display information and result
        print("Cosine similarity:", cosine_similarity)
        epsilon = 0.2  # Threshold for verification

        is_match = cosine_similarity < epsilon

        if is_match:
            print("Verify: Face matched")
        else:
            print("Do not verify: Face not matched")

        return is_match  # Return the boolean result

    def cosineDistance(face1_features, face2_features):
        # Ensure the input arrays are 1D
        face1_features = np.array(face1_features).flatten()
        face2_features = np.array(face2_features).flatten()

        if face1_features.shape != face2_features.shape:
            # log the shapes and log min size
            logger.error(
                f"Shape mismatch: {face1_features.shape} vs {face2_features.shape}")
            min_size = min(face1_features.size, face2_features.size)
            logger.info(f"Minimum size for shapes: {min_size}")
            face1_features = face1_features[:min_size]
            face2_features = face2_features[:min_size]

        # Compute cosine similarity
        dot_product = np.dot(face1_features, face2_features)
        norm_a = np.linalg.norm(face1_features)
        norm_b = np.linalg.norm(face2_features)

        # calculate the cosine distance
        return 1 - (dot_product / (norm_a * norm_b))

    def real_perform_recognition(filename1, filename2):
        image = cv2.imread(filename1)
        image2 = cv2.imread(filename2)

        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

        # Detect faces in both images
        faces = face_cascade.detectMultiScale(gray_image, 1.3, 5)
        employee_faces = face_cascade.detectMultiScale(gray_image2, 1.3, 5)

        if len(faces) == 0:
            print("No faces detected in one of the images.")
            return False  # Return False when faces can't be detected
        if len(employee_faces) == 0:
            print("Error detecting employee face")
            return False  # Return False when faces can't be detected

        # Crop the first detected face in each image
        # Assuming at least one face is found
        cropped_face = crop_faces(image, faces)[0]
        cropped_employee_face = crop_faces(image2, employee_faces)[0]

        # Verify the two cropped faces and return the result
        return verify_face(cropped_face, cropped_employee_face)


def run_tests():
    """Run multiple face recognition test scenarios"""
    # Get absolute paths to test files
    scripts_path = os.path.dirname(os.path.abspath(__file__))

    test_cases = [
        {
            "name": "Same person test",
            "img1": os.path.join(scripts_path, 'test_images', 'person1_img1.jpg'),
            "img2": os.path.join(scripts_path, 'test_images', 'person1_img2.jpg'),
            "expected": True
        },
        {
            "name": "Different person test",
            "img1": os.path.join(scripts_path, 'test_images', 'person1_img1.jpg'),
            "img2": os.path.join(scripts_path, 'test_images', 'person2_img1.png'),
            "expected": False
        },
        {
            "name": "Different facial expressions test",
            "img1": os.path.join(scripts_path, 'test_images', 'person1_smile.jpg'),
            "img2": os.path.join(scripts_path, 'test_images', 'person1_nosmile.jpg'),
            "expected": True
        }
    ]
    for test in test_cases:
        print(f"\nRunning test: {test['name']}")
        result = perform_recognition(test['img1'], test['img2'])
        print(f"Result: {'PASS' if result == test['expected'] else 'FAIL'}")


if __name__ == "__main__":
    run_tests()
