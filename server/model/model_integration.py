from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Input, Convolution2D, ZeroPadding2D, MaxPooling2D, Flatten, Dense, Dropout, Activation
from PIL import Image
from tensorflow.keras.preprocessing.image import load_img, save_img, img_to_array
from tensorflow.keras.applications.imagenet_utils import preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.preprocessing.image import load_img
from base64 import b64decode, b64encode
from tensorflow.keras.models import model_from_json
import matplotlib.pyplot as plt
import cv2
import numpy as np
import PIL
import io


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


def generate_embedding(image_input):
    if USE_DUMMY_EMBEDDING:
        return dummy_generate_embedding(image_input)
    else:
        return real_generate_embedding(image_input)


def dummy_generate_embedding(image_input):
    return [0.1] * 128


def real_generate_embedding(image_input):
    embeddings = facial_features.predict(preprocess_image(image_input))[0, :]
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
    cosine_similarity = cosineSimilarity(face1_embedding, face2_embedding)

    # Display information and result
    print("Cosine similarity:", cosine_similarity)
    epsilon = 0.2  # Threshold for verification

    if cosine_similarity < epsilon:
        print("Verify: Face matched")
    else:
        print("Do not verify: Face not matched")


def cosineSimilarity(face1_features, face2_features):
    # Ensure the input arrays are 1D
    face1_features = np.array(face1_features).flatten()
    face2_features = np.array(face2_features).flatten()

    # Compute cosine similarity
    dot_product = np.dot(face1_features, face2_features)
    norm_a = np.linalg.norm(face1_features)
    norm_b = np.linalg.norm(face2_features)

    return 1 - (dot_product / (norm_a * norm_b))


def perform_recognition(filename, filename2):
    # TODO: Thomas - update these to work with images sent from the Arduino and the database
    image = cv2.imread(filename)
    image2 = cv2.imread(filename2)

    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

    # Detect faces in both images
    faces = face_cascade.detectMultiScale(gray_image, 1.3, 5)
    employee_faces = face_cascade.detectMultiScale(gray_image2, 1.3, 5)

    if len(faces) == 0:
        print("No faces detected in one of the images.")
        return
    if len(employee_faces) == 0:
        print("error detecting employee face")
        return

    # Crop the first detected face in each image
    # Assuming at least one face is found
    cropped_face = crop_faces(image, faces)[0]
    cropped_employee_face = crop_faces(image2, employee_faces)[0]

    # Verify the two cropped faces
    verify_face(cropped_face, cropped_employee_face)


# Paths to the test images
esp32_image = r'model\image.png'
db_image = r'model\image2.png'

# Call the perform_recognition function with the test images
# perform_recognition(esp32_image, db_image)
