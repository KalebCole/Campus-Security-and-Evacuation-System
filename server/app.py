from flask import Flask
from app_config import Config
from flask_cors import CORS
import logging
# Import and register routes
from routes import routes_bp
import os
from dotenv import load_dotenv

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS
    CORS(app)

    app.register_blueprint(routes_bp, url_prefix='/api')

    @app.route("/", methods=['GET'])
    def index():
        return "This is the flask app"

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
