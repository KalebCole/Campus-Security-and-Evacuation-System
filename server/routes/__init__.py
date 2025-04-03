"""Routes initialization module - imports and registers all route modules."""
from .verification_routes import *
from .system_routes import *
from flask import Blueprint

# Create the main routes blueprint
routes_bp = Blueprint('routes', __name__)

# Import route modules

# You can register other route modules here when implemented
# from .notification_routes import *
