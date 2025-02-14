from flask import Flask
from config import Config
from flask_cors import CORS

# from supabase_client import supabase
from routes.mock_routes import mock_bp
from routes.routes import routes_bp
# ========================
# Initialize the Flask app
# ========================


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS if needed
    CORS(app)

    # Register blueprints
    app.register_blueprint(mock_bp, url_prefix='/api')

    # blueprint for the input verification from RFID and facial recognition
    app.register_blueprint(routes_bp, url_prefix='/api')

    @app.route("/", methods=['GET'])
    def index():
        return "This is the flask app"
    return app


app = create_app()


# Expecting a JSON object with a base64 image
# example payload:
# {
#     "base64_image": "base64_encoded_image_here"
# }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
