from flask import Flask
from app_config import Config
from flask_cors import CORS

# from supabase_client import supabase
from routes import routes_bp
# ========================
# Initialize the Flask app
# ========================


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS if needed
    CORS(app)

    # Register blueprints
    # main routes, logic blueprint
    app.register_blueprint(routes_bp, url_prefix='/api')

    @app.route("/", methods=['GET'])
    def index():
        return "This is the flask app"
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
