import base64
from flask import Flask, jsonify, request
from supabase import create_client, Client
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Supabase client
supabase_url = app.config['SUPABASE_URL']
supabase_key = app.config['SUPABASE_API_KEY']
supabase: Client = create_client(supabase_url, supabase_key)


@app.route("/", methods=['GET'])
def index():
    return "This is the flask app"


@app.route('/get-users', methods=['GET'])
def get_users():
    # Query the 'users' table in Supabase
    response = supabase.table('User Entries').select('*').execute()
    print("in get users")
    print(response)
    return jsonify(response.data)


# Example route to receive image data
@app.route('/upload-image', methods=['POST'])
def upload_image():
    data = request.get_json()

    # Extract the image data from the POST request
    image_data = data.get('image')
    if image_data:
        # Decode the base64-encoded image
        image_bytes = base64.b64decode(image_data)

        # Save the image locally (or upload to Supabase/cloud storage)
        with open('received_image.jpg', 'wb') as f:
            f.write(image_bytes)

        return jsonify({"message": "Image received successfully"}), 200
    else:
        return jsonify({"error": "No image provided"}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
