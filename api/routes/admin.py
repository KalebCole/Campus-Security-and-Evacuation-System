import logging
import base64
from flask import Blueprint, request, jsonify, abort, current_app, render_template, url_for, redirect, flash, Response, send_file
from uuid import UUID
from datetime import datetime
from io import BytesIO

from services.database import DatabaseService
from services.mqtt_service import MQTTService
from models.access_log import AccessLog
from models.employee import Employee

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')


@admin_bp.route('/reviews/pending', methods=['GET'])
def get_pending_reviews():
    """Get a list of sessions pending manual review and render HTML."""
    logger.info("GET /admin/reviews/pending received")
    try:
        db_service: DatabaseService = current_app.db_service
        pending_reviews_data = db_service.get_pending_review_sessions()
        # Render the HTML template, passing the list of reviews
        return render_template('admin/pending_reviews.html', pending_reviews=pending_reviews_data)
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}", exc_info=True)
        flash("Error loading pending reviews.", "error")
        # Render the template even on error, but with an empty list or error message shown via flash
        return render_template('admin/pending_reviews.html', pending_reviews=[])


@admin_bp.route('/reviews/<uuid:session_id>', methods=['GET'])
def get_review_details(session_id: UUID):
    """Get detailed information for a specific session review and render HTML."""
    logger.info(f"GET /admin/reviews/{session_id} received")
    try:
        db_service: DatabaseService = current_app.db_service
        details_dict = db_service.get_session_review_details(str(session_id))

        if details_dict is None:
            flash(
                f"Review details not found for session ID: {session_id}", "warning")
            return redirect(url_for('admin_bp.get_pending_reviews'))

        # No need to serialize manually with model_to_dict anymore
        # The details_dict directly contains AccessLog/Employee objects and lists/dicts
        return render_template('admin/review_details.html', details=details_dict)

    except Exception as e:
        logger.error(
            f"Error getting review details for {session_id}: {e}", exc_info=True)
        flash(f"Error loading details for session {session_id}.", "error")
        return redirect(url_for('admin_bp.get_pending_reviews'))


@admin_bp.route('/reviews/<uuid:session_id>/approve', methods=['POST'])
def approve_review(session_id: UUID):
    """Approve access for a reviewed session via POST, then redirect."""
    logger.info(f"POST /admin/reviews/{session_id}/approve received")
    session_id_str = str(session_id)
    try:
        db_service: DatabaseService = current_app.db_service
        mqtt_service: MQTTService = current_app.mqtt_service

        # Update the status in the database
        updated = db_service.update_review_status(
            session_id=session_id_str, approved=True)

        if not updated:
            flash(
                f"Could not approve session {session_id}. It might not be pending or might not exist.", "warning")
        else:
            # If update was successful, publish unlock command
            logger.info(
                f"Session {session_id} approved by admin. Publishing unlock command.")
            mqtt_service._publish_unlock(session_id=session_id_str)
            flash(f"Session {session_id} approved successfully.", "success")
            # TODO: Log action to admin audit log (when implemented)

    except Exception as e:
        logger.error(
            f"Error approving review for {session_id}: {e}", exc_info=True)
        flash(
            f"An error occurred while approving session {session_id}.", "error")

    # Redirect back to the pending reviews list regardless of success/failure
    return redirect(url_for('admin_bp.get_pending_reviews'))


@admin_bp.route('/reviews/<uuid:session_id>/deny', methods=['POST'])
def deny_review(session_id: UUID):
    """Deny access for a reviewed session via POST, then redirect."""
    logger.info(f"POST /admin/reviews/{session_id}/deny received")
    session_id_str = str(session_id)
    try:
        db_service: DatabaseService = current_app.db_service

        # Update the status in the database
        updated = db_service.update_review_status(
            session_id=session_id_str, approved=False)

        if not updated:
            flash(
                f"Could not deny session {session_id}. It might not be pending or might not exist.", "warning")
        else:
            logger.info(f"Session {session_id} denied by admin.")
            flash(f"Session {session_id} denied successfully.", "success")
            # TODO: Log action to admin audit log (when implemented)

    except Exception as e:
        logger.error(
            f"Error denying review for {session_id}: {e}", exc_info=True)
        flash(
            f"An error occurred while denying session {session_id}.", "error")

    # Redirect back to the pending reviews list
    return redirect(url_for('admin_bp.get_pending_reviews'))


@admin_bp.route('/image/<uuid:session_id>', methods=['GET'])
def get_verification_image(session_id: UUID):
    """Serves the verification image associated with a session ID."""
    logger.debug(f"GET /admin/image/{session_id} received")
    session_id_str = str(session_id)
    try:
        db_service: DatabaseService = current_app.db_service
        image_data = db_service.get_verification_image_data(session_id_str)

        if image_data is None:
            logger.warning(
                f"Verification image not found for session_id: {session_id_str}")
            # Optionally, return a placeholder image or 404
            # For now, returning 404
            abort(404, description="Verification image not found.")

        # Assume JPEG format for now. Ideally, store/infer mimetype.
        mimetype = 'image/jpeg'

        # Use send_file for simpler handling of binary data
        return send_file(BytesIO(image_data), mimetype=mimetype)

    except Exception as e:
        logger.error(
            f"Error serving verification image for {session_id_str}: {e}", exc_info=True)
        abort(500)
