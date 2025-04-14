from flask import Flask
from routes.session import bp as session_bp, init_db_service
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database service
init_db_service(app.config['DATABASE_URL'])

# Register blueprints
app.register_blueprint(session_bp)


@app.route('/')
def health_check():
    """Health check endpoint."""
    return {'status': 'healthy'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=app.config['DEBUG'])
