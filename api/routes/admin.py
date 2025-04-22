import logging
import base64
from flask import Blueprint, request, jsonify, abort, current_app, render_template, url_for, redirect, flash, Response, send_file
from uuid import UUID
from datetime import datetime, date
from io import BytesIO
from werkzeug.utils import secure_filename
import os
from typing import List, Dict
import uuid
import sqlalchemy.exc

from services.database import DatabaseService
from services.mqtt_service import MQTTService
from models.access_log import AccessLog
from models.employee import Employee
from services.face_recognition_client import FaceRecognitionClient, FaceRecognitionClientError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

# --- Helper for file uploads (M11) ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@admin_bp.route('/reviews', methods=['GET'])
def get_reviews():
    """Display Pending, Today's, and Previous access logs (paginated)."""
    logger.info("GET /admin/reviews received")
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    try:
        db_service: DatabaseService = current_app.db_service

        # Fetch data for each section
        pending_logs = db_service.get_pending_review_sessions()  # Pending are not paginated
        today_logs = db_service.get_todays_logs()             # Today's are not paginated
        previous_logs, total_previous = db_service.get_previous_resolved_logs(
            page=page, per_page=per_page)

        # Calculate pending count for the badge
        pending_count = len(pending_logs)

        # Simple pagination calculation
        total_pages = (total_previous + per_page - 1) // per_page

        # Render the new template, passing all data including pagination info
        return render_template(
            'admin/reviews.html',
            pending_logs=pending_logs,
            today_logs=today_logs,
            previous_logs=previous_logs,
            pending_count=pending_count,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            total_previous=total_previous
        )
    except Exception as e:
        logger.error(f"Error loading reviews page: {e}", exc_info=True)
        flash("Error loading access logs.", "error")
        # Render template with empty lists on error, passing 0 count and basic pagination defaults
        return render_template('admin/reviews.html', pending_logs=[], today_logs=[], previous_logs=[], pending_count=0, current_page=1, total_pages=0, per_page=per_page, total_previous=0)


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
            # Redirect to the main reviews page now
            return redirect(url_for('admin_bp.get_reviews'))

        # Pass pending count to details view as well so base template badge works
        pending_count = len(db_service.get_pending_review_sessions())

        return render_template('admin/review_details.html', details=details_dict, pending_count=pending_count)

    except Exception as e:
        logger.error(
            f"Error getting review details for {session_id}: {e}", exc_info=True)
        flash(f"Error loading details for session {session_id}.", "error")
        # Redirect to the main reviews page now
        return redirect(url_for('admin_bp.get_reviews'))


@admin_bp.route('/reviews/<uuid:session_id>/approve', methods=['POST'])
def approve_review(session_id: UUID):
    """Approve access for a reviewed session via POST, then redirect."""
    logger.info(f"POST /admin/reviews/{session_id}/approve received")
    session_id_str = str(session_id)
    selected_employee_id = request.form.get('selected_employee_id')
    logger.debug(
        f"Form data received: selected_employee_id={selected_employee_id}")

    try:
        db_service: DatabaseService = current_app.db_service
        mqtt_service: MQTTService = current_app.mqtt_service
        access_log = db_service.get_access_log_by_session_id(session_id_str)

        if not access_log:
            flash(
                f"Access log not found for session {session_id}. Cannot approve.", "error")
            # Redirect to main reviews page
            return redirect(url_for('admin_bp.get_reviews'))

        if access_log.verification_method == 'FACE_ONLY_PENDING_REVIEW' and not selected_employee_id:
            flash(
                "Error: You must select an employee match to approve a Face-Only review.", "error")
            return redirect(url_for('admin_bp.get_review_details', session_id=session_id))

        updated = db_service.update_review_status(
            session_id=session_id_str,
            approved=True,
            employee_id=selected_employee_id
        )

        if not updated:
            flash(
                f"Could not approve session {session_id}. It might not be pending or might not exist.", "warning")
        else:
            logger.info(
                f"Session {session_id} approved by admin (Employee association: {selected_employee_id or 'N/A'}). Publishing unlock command.")
            mqtt_service._publish_unlock(session_id=session_id_str)
            flash(f"Session {session_id} approved successfully.", "success")

    except Exception as e:
        logger.error(
            f"Error approving review for {session_id}: {e}", exc_info=True)
        flash(
            f"An error occurred while approving session {session_id}.", "error")

    # Redirect back to the main reviews list
    return redirect(url_for('admin_bp.get_reviews'))


@admin_bp.route('/reviews/<uuid:session_id>/deny', methods=['POST'])
def deny_review(session_id: UUID):
    """Deny access for a reviewed session via POST, then redirect."""
    logger.info(f"POST /admin/reviews/{session_id}/deny received")
    session_id_str = str(session_id)
    try:
        db_service: DatabaseService = current_app.db_service
        updated = db_service.update_review_status(
            session_id=session_id_str, approved=False)

        if not updated:
            flash(
                f"Could not deny session {session_id}. It might not be pending or might not exist.", "warning")
        else:
            logger.info(f"Session {session_id} denied by admin.")
            flash(f"Session {session_id} denied successfully.", "success")

    except Exception as e:
        logger.error(
            f"Error denying review for {session_id}: {e}", exc_info=True)
        flash(
            f"An error occurred while denying session {session_id}.", "error")

    # Redirect back to the main reviews list
    return redirect(url_for('admin_bp.get_reviews'))


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
            abort(404, description="Verification image not found.")

        mimetype = 'image/jpeg'
        return send_file(BytesIO(image_data), mimetype=mimetype)

    except Exception as e:
        logger.error(
            f"Error serving verification image for {session_id_str}: {e}", exc_info=True)
        abort(500)


# --- Employee Management Routes (Milestone 10 & 11) ---

@admin_bp.route('/employees', methods=['GET'])
def employees_list():
    """Display a list of all employees."""
    logger.info("GET /admin/employees received")
    try:
        db_service: DatabaseService = current_app.db_service
        employees = db_service.get_all_employees(
            include_inactive=True)  # Show all for management
        # For base template
        pending_count = len(db_service.get_pending_review_sessions())
        return render_template('admin/employees_list.html', employees=employees, pending_count=pending_count)
    except Exception as e:
        logger.error(f"Error fetching employee list: {e}", exc_info=True)
        flash("Failed to load employee list.", "error")
        # Render empty on error
        return render_template('admin/employees_list.html', employees=[], pending_count=0)


@admin_bp.route('/employees/new', methods=['GET'])
def employees_new_form():
    """Display the form to create a new employee."""
    logger.info("GET /admin/employees/new received")
    db_service: DatabaseService = current_app.db_service
    # For base template
    pending_count = len(db_service.get_pending_review_sessions())
    # Pass an empty dictionary or specific defaults if needed for the form template
    return render_template('admin/employee_form.html', employee=None, is_edit=False, pending_count=pending_count)


@admin_bp.route("/employees/create", methods=["POST"])
def employees_create():
    """Create a new employee."""
    try:
        # Extract form data
        name = request.form.get("name")
        rfid_tag = request.form.get("rfid_tag")
        role = request.form.get("role")
        email = request.form.get("email")
        active = request.form.get("active", "true").lower() == "true"
        photo = request.files.get("photo")

        # Validate required fields
        if not all([name, rfid_tag, role, email]):
            flash(
                "Missing required fields. Please fill in all required information.", "error")
            return render_template('admin/employee_form.html',
                                   employee=request.form,
                                   is_edit=False,
                                   pending_count=len(current_app.db_service.get_pending_review_sessions())), 400

        # Start a transaction
        db_service: DatabaseService = current_app.db_service
        face_client: FaceRecognitionClient = current_app.face_client
        session = db_service.get_session()

        # Variables for face embedding
        face_embedding = None

        try:
            # Handle photo upload and face embedding generation first
            if photo and photo.filename:
                try:
                    # Read photo data
                    photo_data = photo.read()

                    # Convert to base64 for the face client
                    photo_base64 = base64.b64encode(photo_data).decode('utf-8')
                    # Add data URI prefix expected by DeepFace client
                    mime_type = photo.mimetype or 'image/jpeg'
                    photo_base64_uri = f"data:{mime_type};base64,{photo_base64}"

                    # Generate face embedding
                    logger.info(
                        f"Generating face embedding for new employee {name}")
                    face_embedding = face_client.get_embedding(
                        photo_base64_uri)
                    if face_embedding:
                        logger.info("Successfully generated face embedding")
                    else:
                        logger.warning("Failed to generate face embedding")
                        flash(
                            "Could not generate face embedding from the photo. The employee will be created without face recognition capability.", "warning")

                    # Reset file pointer for later use
                    photo.seek(0)
                except Exception as embed_err:
                    logger.error(
                        f"Error generating face embedding: {embed_err}", exc_info=True)
                    flash(
                        "Failed to process the photo for face recognition. The employee will be created without face recognition capability.", "warning")
                    # Reset file pointer
                    photo.seek(0)

            # Create employee with the embedding if we got one
            employee = db_service.create_employee_with_session(
                session=session,
                name=name,
                rfid_tag=rfid_tag,
                role=role,
                email=email,
                active=active,
                face_embedding=face_embedding  # This might be None if embedding generation failed
            )

            # Handle photo storage if provided
            if photo and photo.filename:
                # Generate a unique session ID for this photo
                photo_session_id = f"employee_creation_{str(uuid.uuid4())}"

                try:
                    # Read photo data (we already reset the file pointer)
                    photo_data = photo.read()

                    # Save the verification image
                    verification_image = db_service.save_verification_image_with_session(
                        session=session,
                        session_id=photo_session_id,
                        image_data=photo_data,
                        device_id="web_admin",
                        matched_employee_id=employee.id,
                        embedding=face_embedding,  # Store the embedding with the verification image
                        processed=True,
                        status="employee_photo"
                    )

                    # Update employee with photo URL
                    employee.photo_url = f"/api/verification_images/{verification_image.id}/image"
                    session.flush()
                except Exception as photo_err:
                    logger.error(
                        f"Error processing photo upload: {photo_err}", exc_info=True)
                    flash(
                        "Failed to save the photo. Employee was created but without a photo.", "warning")

            # If we got here, commit the transaction
            session.commit()

            flash(f"Employee '{name}' created successfully!", "success")
            if face_embedding:
                flash(
                    "Face recognition capability has been enabled for this employee.", "success")
            return redirect(url_for('admin_bp.employees_list'))

        except sqlalchemy.exc.IntegrityError as ie:
            session.rollback()
            error_message = str(ie).lower()
            if "rfid_tag" in error_message:
                flash(
                    f"An employee with RFID tag '{rfid_tag}' already exists.", "error")
            elif "email" in error_message:
                flash(
                    f"An employee with email '{email}' already exists.", "error")
            else:
                flash(
                    "A database error occurred. Please check your input and try again.", "error")

            # Re-render the form with the submitted data
            return render_template('admin/employee_form.html',
                                   employee=request.form,
                                   is_edit=False,
                                   pending_count=len(db_service.get_pending_review_sessions())), 409
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating employee: {e}", exc_info=True)
            flash(
                "An unexpected error occurred while creating the employee. Please try again.", "error")
            return render_template('admin/employee_form.html',
                                   employee=request.form,
                                   is_edit=False,
                                   pending_count=len(db_service.get_pending_review_sessions())), 500
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error in employee creation route: {e}", exc_info=True)
        flash("An unexpected error occurred. Please try again.", "error")
        return render_template('admin/employee_form.html',
                               employee=None,
                               is_edit=False,
                               pending_count=len(current_app.db_service.get_pending_review_sessions())), 500


@admin_bp.route('/employees/<uuid:employee_id>/edit', methods=['GET'])
def employees_edit_form(employee_id: UUID):
    """Display the form to edit an existing employee."""
    logger.info(f"GET /admin/employees/{employee_id}/edit received")
    try:
        db_service: DatabaseService = current_app.db_service
        employee = db_service.get_employee_by_id(employee_id)
        if not employee:
            flash(f"Employee with ID {employee_id} not found.", "error")
            return redirect(url_for('admin_bp.employees_list'))

        # For base template
        pending_count = len(db_service.get_pending_review_sessions())
        return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count)
    except Exception as e:
        logger.error(
            f"Error loading edit form for employee {employee_id}: {e}", exc_info=True)
        flash("Failed to load employee edit form.", "error")
        return redirect(url_for('admin_bp.employees_list'))


@admin_bp.route('/employees/<uuid:employee_id>/edit', methods=['POST'])
def employees_edit(employee_id: UUID):
    """Handle updating an existing employee, including photo upload and embedding."""
    logger.info(f"POST /admin/employees/{employee_id}/edit received")
    db_service: DatabaseService = current_app.db_service
    face_client: FaceRecognitionClient = current_app.face_client  # Get face client

    employee = db_service.get_employee_by_id(employee_id)
    if not employee:
        flash(
            f"Employee with ID {employee_id} not found. Cannot update.", "error")
        return redirect(url_for('admin_bp.employees_list'))

    # Extract form data
    update_data = {
        'name': request.form.get('name'),
        'rfid_tag': request.form.get('rfid_tag'),
        'role': request.form.get('role'),
        'email': request.form.get('email'),
        'active': request.form.get('active') == 'on'
    }

    # Basic validation
    if not all([update_data['name'], update_data['rfid_tag'], update_data['role'], update_data['email']]):
        flash("Missing required employee fields.", "warning")
        pending_count = len(db_service.get_pending_review_sessions())
        # Use a dict that mimics employee object for re-rendering form
        form_data_for_template = employee.__dict__.copy()
        # Overlay potentially bad data for user correction
        form_data_for_template.update(request.form.to_dict())
        return render_template('admin/employee_form.html', employee=form_data_for_template, is_edit=True, pending_count=pending_count), 400

    # --- Handle Photo Upload and Embedding ---
    photo_file = request.files.get('photo')
    new_embedding = None
    temp_photo_url_for_embedding = None  # We don't have a final URL yet

    if photo_file and photo_file.filename != '' and allowed_file(photo_file.filename):
        logger.info(f"Processing uploaded photo for employee {employee_id}")
        try:
            # Read file into memory for processing
            image_bytes = photo_file.read()
            # Encode to base64 for the face client
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            # Add data URI prefix expected by DeepFace client
            mime_type = photo_file.mimetype
            image_base64_uri = f"data:{mime_type};base64,{image_base64}"

            logger.debug(
                f"Calling face client to get embedding for employee {employee_id}")
            new_embedding = face_client.get_embedding(image_base64_uri)

            if new_embedding:
                update_data['face_embedding'] = new_embedding
                logger.info(
                    f"New face embedding generated for employee {employee_id}.")

                # Save to verification_images first
                session_id = str(uuid.uuid4())  # Generate a unique session ID
                verification_image = db_service.save_verification_image(
                    session_id=session_id,
                    image_data=image_bytes,
                    device_id='EMPLOYEE_PHOTO',
                    matched_employee_id=employee_id,
                    embedding=new_embedding,
                    processed=True
                )

                if verification_image:
                    # Create URL for the verification image
                    photo_url = url_for(
                        'admin_bp.get_verification_image', session_id=session_id, _external=True)
                    update_data['photo_url'] = photo_url
                    logger.info(
                        f"Saved new photo for employee {employee_id}. URL: {photo_url}")
                else:
                    flash("Failed to save the photo. Please try again.", "error")
            else:
                flash(
                    "Could not generate face embedding from the uploaded photo. Photo not saved.", "warning")

        except FaceRecognitionClientError as e:
            logger.error(
                f"Face recognition client error for employee {employee_id}: {e}")
            flash(
                f"Error generating face embedding: {e}. Photo not saved.", "error")
        except Exception as e:
            logger.error(
                f"Error processing photo upload for employee {employee_id}: {e}", exc_info=True)
            flash("An unexpected error occurred while processing the photo.", "error")
            pending_count = len(db_service.get_pending_review_sessions())
            return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count), 500
    elif photo_file and photo_file.filename != '' and not allowed_file(photo_file.filename):
        flash("Invalid file type for photo. Please upload PNG or JPG.", "warning")
        pending_count = len(db_service.get_pending_review_sessions())
        return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count), 400

    try:
        updated_employee = db_service.update_employee(employee_id, update_data)

        if updated_employee:
            flash(
                f"Employee '{updated_employee.name}' updated successfully.", "success")
            return redirect(url_for('admin_bp.employees_list'))
        else:
            flash(f"Failed to update employee. RFID tag or Email might already exist for another employee.", "error")
            pending_count = len(db_service.get_pending_review_sessions())
            form_data_for_template = employee.__dict__.copy()
            form_data_for_template.update(request.form.to_dict())
            return render_template('admin/employee_form.html', employee=form_data_for_template, is_edit=True, pending_count=pending_count), 400

    except Exception as e:
        logger.error(
            f"Error updating employee in database {employee_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while updating the employee.", "error")
        pending_count = len(db_service.get_pending_review_sessions())
        return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count), 500


@admin_bp.route('/employees/<uuid:employee_id>/delete', methods=['POST'])
def employees_delete(employee_id: UUID):
    """Handle deleting an employee."""
    logger.info(f"POST /admin/employees/{employee_id}/delete received")
    # Add CSRF protection in a real app!
    try:
        db_service: DatabaseService = current_app.db_service
        # Optional: Check for dependencies before deleting? (e.g., access logs)

        employee = db_service.get_employee_by_id(
            employee_id)  # Get name for flash message
        if not employee:
            flash(
                f"Employee with ID {employee_id} not found. Cannot delete.", "error")
            return redirect(url_for('admin_bp.employees_list'))

        deleted = db_service.delete_employee(employee_id)

        if deleted:
            # TODO: Delete associated photo file if stored locally
            if employee.photo_url and employee.photo_url.startswith(url_for('static', filename='uploads/employees/')):
                try:
                    # Derive file path from URL
                    filename = employee.photo_url.split('/')[-1]
                    file_path = os.path.join(
                        current_app.static_folder, 'uploads', 'employees', filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(
                            f"Deleted photo file {file_path} for employee {employee_id}")
                except Exception as file_del_err:
                    logger.error(
                        f"Error deleting photo file for employee {employee_id}: {file_del_err}", exc_info=True)

            flash(
                f"Employee '{employee.name}' deleted successfully.", "success")
        else:
            flash(
                f"Failed to delete employee '{employee.name}'. Check logs for details (e.g., dependencies).", "error")

    except Exception as e:
        logger.error(
            f"Error processing delete request for employee {employee_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while deleting the employee.", "error")

    return redirect(url_for('admin_bp.employees_list'))

# --- API Endpoints for Frontend (e.g., status polling) ---


@admin_bp.route('/api/status/emergency', methods=['GET'])
def get_emergency_status():
    """API endpoint to check the current emergency status.
    This endpoint avoids database hits by using the app's global state."""
    # Access the global variable directly from app context
    # No database query needed
    return jsonify({
        "emergency_active": current_app.emergency_active,
        "timestamp": datetime.utcnow().isoformat()
    })


@admin_bp.route('/api/verification_images/<uuid:image_id>/image', methods=['GET'])
def get_verification_image_by_id(image_id: uuid.UUID):
    """Serves a verification image by its ID."""
    try:
        db_service: DatabaseService = current_app.db_service
        image_data = db_service.get_verification_image_data_by_id(
            str(image_id))

        if image_data is None:
            logger.warning(f"Verification image not found for ID: {image_id}")
            return abort(404)

        return send_file(
            BytesIO(image_data),
            mimetype='image/jpeg',
            as_attachment=False
        )
    except Exception as e:
        logger.error(
            f"Error serving verification image {image_id}: {e}", exc_info=True)
        return abort(500)
