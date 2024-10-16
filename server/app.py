import base64
import uuid
from flask import Flask, jsonify, request
from config import Config
from flask_cors import CORS
from supabase_client import supabase
from routes.verification import verification_bp

# ========================
# Initialize the Flask app
# ========================


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS if needed
    CORS(app)

    # Register blueprints

    # blueprint for the input verification from RFID and facial recognition
    app.register_blueprint(verification_bp, url_prefix='/api')

    @app.route("/", methods=['GET'])
    def index():
        return "This is the flask app"

    return app


app = create_app()

# Supabase tables and storage
user_table = supabase.table(app.config['SUPABASE_USER_TABLE'])
storage_bucket = supabase.storage.get_bucket(
    app.config['SUPABASE_STORAGE_BUCKET'])
user_entries_storage_path = app.config['SUPABASE_USER_ENTRIES_STORAGE_PATH']


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


# ========================
# Routes for the Frontend


@app.route('/get-users', methods=['GET'])
def get_users():
    # Query the 'users' table in Supabase
    response = user_table.select('*').execute()

    # Print the response for debugging
    print("in get users")
    print(response)
    # response data
    print("response data: " + str(response.data))

    print("json response data" + str(jsonify(response.data)))

    # Return the data portion of the response
    if response.data:
        return jsonify(response.data), 200
    else:
        return jsonify({"error": "No data found"}), 404


# Expecting a JSON object with a base64 image
# example payload:
@app.route('/upload-image', methods=['POST'])
def upload_image():

    data = request.get_json()
    # validate the request
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # validate the image data
    if 'base64_image' not in data:
        return jsonify({"error": "No image provided"}), 400

    # Extract the image data from the POST request
    image_data = data.get('base64_image')
    if image_data:
        # Decode the base64-encoded image
        image_bytes = base64.b64decode(image_data)

        # Generate a unique file name or use a provided one
        unique_filename = str(uuid.uuid4()) + '.jpg'
        path_on_supastorage = f'{user_entries_storage_path}/{unique_filename}'

        # Upload the image bytes to Supabase storage
        response = storage_bucket.upload(
            path=path_on_supastorage, file=image_bytes, file_options={"content-type": "image/jpeg"})

        # Check if the image was uploaded successfully
        if response.status_code != 200:
            return jsonify({"error": "Failed to upload image"}), 500

        # fetch from the storage
        image_url = storage_bucket.get_public_url(path_on_supastorage)
        print(image_url)

        # validate the response
        if not image_url:
            return jsonify({"error": "Failed to get image url"}), 500

        # insert the user into the table
        user = {"photo_url": image_url}
        response = user_table.insert(user).execute()
        print(response)

        # validate the response
        if not response:
            return jsonify({"error": "Failed to insert user"}), 500

        return jsonify({"message": "Image received successfully"}), 200
    else:
        return jsonify({"error": "No image provided"}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)