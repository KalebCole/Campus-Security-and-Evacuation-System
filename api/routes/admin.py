import logging
import base64
from flask import Blueprint, request, jsonify, abort, current_app
from uuid import UUID
from datetime import datetime

from services.database import DatabaseService
from services.mqtt_service import MQTTService
from models.access_log import AccessLog
from models.employee import Employee

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Helper to serialize SQLAlchemy model objects


def model_to_dict(model):
    if model is None:
        return None
    # Basic serialization, customize as needed
    d = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, UUID):
            d[column.name] = str(value)
        elif isinstance(value, datetime):  # Import datetime if needed
            d[column.name] = value.isoformat()
        elif column.name == 'face_embedding':  # Exclude large fields like embeddings
            continue
        else:
            d[column.name] = value
    return d


@admin_bp.route('/reviews/pending', methods=['GET'])
def get_pending_reviews():
    """Get a list of sessions pending manual review."""
    logger.info("GET /admin/reviews/pending received")
    try:
        db_service: DatabaseService = current_app.db_service
        # Already returns list of dicts
        pending_reviews = db_service.get_pending_review_sessions()
        return jsonify(pending_reviews), 200
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}", exc_info=True)
        abort(500, description="Internal server error fetching pending reviews.")


@admin_bp.route('/reviews/<uuid:session_id>', methods=['GET'])
def get_review_details(session_id: UUID):
    """Get detailed information for a specific session review."""
    logger.info(f"GET /admin/reviews/{session_id} received")
    try:
        db_service: DatabaseService = current_app.db_service
        # Convert UUID to string for the database service call
        details_dict = db_service.get_session_review_details(str(session_id))

        if details_dict is None:
            abort(
                404, description=f"Review details not found for session ID: {session_id}")

        # Serialize the SQLAlchemy objects within the details dict
        response_data = {
            # Serialize AccessLog
            "access_log": model_to_dict(details_dict.get("access_log")),
            # Serialize Employee
            "employee": model_to_dict(details_dict.get("employee")),
            # Already prepared
            "verification_images": details_dict.get("verification_images", []),
            # Already prepared
            "potential_matches": details_dict.get("potential_matches", [])
        }

        return jsonify(response_data), 200
    except Exception as e:
        logger.error(
            f"Error getting review details for {session_id}: {e}", exc_info=True)
        abort(500, description="Internal server error fetching review details.")


@admin_bp.route('/reviews/<uuid:session_id>/approve', methods=['POST'])
def approve_review(session_id: UUID):
    """Approve access for a reviewed session."""
    logger.info(f"POST /admin/reviews/{session_id}/approve received")
    try:
        db_service: DatabaseService = current_app.db_service
        mqtt_service: MQTTService = current_app.mqtt_service
        session_id_str = str(session_id)

        # Update the status in the database
        updated = db_service.update_review_status(
            session_id=session_id_str, approved=True)

        if not updated:
            # Could be not found, or already reviewed
            abort(
                400, description=f"Could not approve session {session_id}. It might not be pending or might not exist.")

        # If update was successful, publish unlock command
        logger.info(
            f"Session {session_id} approved by admin. Publishing unlock command.")
        mqtt_service._publish_unlock(session_id=session_id_str)

        # TODO: Log action to admin audit log (when implemented)

        return jsonify({"status": "success", "message": f"Session {session_id} approved."}), 200
    except Exception as e:
        logger.error(
            f"Error approving review for {session_id}: {e}", exc_info=True)
        abort(500, description="Internal server error approving review.")


@admin_bp.route('/reviews/<uuid:session_id>/deny', methods=['POST'])
def deny_review(session_id: UUID):
    """Deny access for a reviewed session."""
    logger.info(f"POST /admin/reviews/{session_id}/deny received")
    try:
        db_service: DatabaseService = current_app.db_service
        session_id_str = str(session_id)

        # Update the status in the database
        updated = db_service.update_review_status(
            session_id=session_id_str, approved=False)

        if not updated:
            # Could be not found, or already reviewed
            abort(
                400, description=f"Could not deny session {session_id}. It might not be pending or might not exist.")

        # TODO: Log action to admin audit log (when implemented)

        logger.info(f"Session {session_id} denied by admin.")
        return jsonify({"status": "success", "message": f"Session {session_id} denied."}), 200
    except Exception as e:
        logger.error(
            f"Error denying review for {session_id}: {e}", exc_info=True)
        abort(500, description="Internal server error denying review.")
