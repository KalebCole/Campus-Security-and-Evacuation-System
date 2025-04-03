"""Routes for system management operations."""
import logging
import time
from datetime import datetime
from flask import jsonify

from . import routes_bp
from app_config import Config
from worker_manager import WorkerManager
from session_manager import SessionManager
from notifications.notification_service import NotificationService

# Configure logging
logger = logging.getLogger(__name__)

# Shared resources (these will be initialized in routes/__init__.py in the future)
notif_service = NotificationService()
session_manager = SessionManager()
worker_manager = WorkerManager(session_manager, notif_service)

# Initialize system state
system_state = {
    "active": False,
    "last_activity": None
}

# System timeout in seconds
SYSTEM_TIMEOUT = 15


@routes_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to check if the API is running."""
    return jsonify({"status": "success", "message": "API is running"}), 200


@routes_bp.route('/activate', methods=['GET'])
def activate_system():
    """Activate the security system and start the worker thread."""
    global system_state

    # Start the worker thread and set system as active
    worker_manager.start_worker()
    system_state["active"] = True
    system_state["last_activity"] = time.time()

    logger.info("[System] Security system activated")
    return jsonify({
        "status": "success",
        "message": "System activated",
        "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
    }), 200


@routes_bp.route('/deactivate', methods=['GET'])
def deactivate_system():
    """Deactivate the security system and stop the worker thread."""
    global system_state

    # Stop the worker thread and mark system as inactive
    worker_manager.stop_worker()
    system_state["active"] = False
    system_state["last_activity"] = None

    logger.info("[System] Security system deactivated")
    return jsonify({
        "status": "success",
        "message": "System deactivated",
        "timestamp": datetime.now().strftime("%d/%m/%Y %I:%M %p")
    }), 200
