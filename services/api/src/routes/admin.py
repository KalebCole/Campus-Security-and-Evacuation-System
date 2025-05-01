import logging
import base64
from flask import Blueprint, request, jsonify, abort, current_app, render_template, url_for, redirect, flash, Response, send_file
from uuid import UUID
from datetime import datetime, date, timedelta
from io import BytesIO
from werkzeug.utils import secure_filename
import os
from typing import List, Dict
import uuid
import sqlalchemy.exc
import time

# Use relative imports for modules within the src package
from ..services.database import DatabaseService
from ..services.mqtt_service import MQTTService
from ..models.access_log import AccessLog
from ..models.employee import Employee
from ..services.face_recognition_client import FaceRecognitionClient, FaceRecognitionClientError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from ..services.storage_service import upload_image_to_supabase, delete_image_from_supabase, extract_object_path_from_url

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

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning("Serving mock data for /admin/reviews")

        # --- Mock Data Generation ---
        fake_pending = [
            {
                'session_id': 'fake-rfid-mismatch-1',
                'timestamp': datetime.now() - timedelta(minutes=5),
                'verification_method': 'RFID_ONLY_PENDING_REVIEW',
                'review_status': 'pending',
                'employee_name': 'Kyle Holliday',
                'verification_image_url': '/static/images/esp32Images/session_2.png'
            },
            {
                'session_id': 'fake-face-match-1',
                'timestamp': datetime.now() - timedelta(minutes=10),
                'verification_method': 'FACE_ONLY_PENDING_REVIEW',
                'review_status': 'pending',
                'employee_name': '',
                'verification_image_url': '/static/images/esp32Images/session_1.png'
            },
        ]

        fake_today = [
            {
                'session_id': 'fake-auto-approve-1',
                'timestamp': datetime.now() - timedelta(hours=1),
                'verification_method': 'BOTH',
                'review_status': 'approved',
                'employee_name': 'Griffin Holbert',
                'verification_image_url': '/static/images/esp32Images/session_2.png'
            },
        ]

        fake_previous = [
            {
                'session_id': 'fake-prev-deny-1',
                'timestamp': datetime.now() - timedelta(days=1, hours=2),
                'verification_method': 'FACE',
                'review_status': 'denied',
                'employee_name': '',
                'verification_image_url': '/static/images/esp32Images/session_3.png'
            },
            {
                'session_id': 'fake-prev-approve-1',
                'timestamp': datetime.now() - timedelta(days=2, hours=5),
                'verification_method': 'RFID',
                'review_status': 'approved',
                'employee_name': 'Luke Reynolds',
                'verification_image_url': '/static/images/esp32Images/session_4.png'
            },

        ]

        pending_count = len(fake_pending)
        total_previous = len(fake_previous)
        page = request.args.get('page', 1, type=int)  # keep pagination
        per_page = request.args.get('per_page', 10, type=int)
        total_pages = (total_previous + per_page - 1) // per_page

        # Simulate pagination slicing for previous logs
        start = (page - 1) * per_page
        end = start + per_page
        paginated_previous = fake_previous[start:end]

        return render_template(
            'admin/reviews.html',
            pending_logs=fake_pending,
            today_logs=fake_today,
            previous_logs=paginated_previous,
            pending_count=pending_count,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            total_previous=total_previous
        )

    else:
        # --- Original Database Logic ---
        logger.info("Fetching real data for /admin/reviews")
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        try:
            db_service: DatabaseService = current_app.db_service

            # Fetch data for each section using session_scope
            with db_service.session_scope() as session:
                pending_logs = db_service.get_pending_review_sessions()
                today_logs = db_service.get_todays_logs()
                previous_logs, total_previous = db_service.get_previous_resolved_logs(
                    page=page, per_page=per_page)
                # pagination for previous logs
                pending_count = len(pending_logs)

                total_pages = (total_previous + per_page - 1) // per_page

                # Render the template with all data
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
            logger.error(
                f"Error loading real reviews page: {e}", exc_info=True)
            flash("Error loading access logs.", "error")
            return render_template('admin/reviews.html',
                                   pending_logs=[],
                                   today_logs=[],
                                   previous_logs=[],
                                   pending_count=0,
                                   current_page=1,
                                   total_pages=0,
                                   per_page=per_page,
                                   total_previous=0)
        # --- End Original Database Logic ---


@admin_bp.route('/reviews/<string:session_id>', methods=['GET'])
def get_review_details(session_id: str):
    """Get detailed information for a specific session review (handles UUIDs or mock strings)."""
    logger.info(f"GET /admin/reviews/{session_id} received")

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning(
            f"Serving mock data for /admin/reviews/{session_id}")

        # --- Mock Data Generation ---
        details_dict = None
        pending_count = 2

        if session_id == 'fake-rfid-mismatch-1':
            details_dict = {
                'access_log': {
                    'session_id': session_id,
                    'timestamp': datetime.now() - timedelta(minutes=5),
                    'verification_method': 'RFID_ONLY_PENDING_REVIEW',
                    'review_status': 'pending',
                    'verification_confidence': 0
                },
                'employee': {
                    'id': 'fake-emp-3',
                    'name': 'Luke Reynolds',
                    'rfid_tag': 'EMP003-FAKE',
                    'role': 'Tester',
                    'email': 'luke@example.com',
                    'photo_url': '/static/images/employees/EMP003.jpg'
                },
                'verification_image_url': '/static/images/esp32Images/session_2.png',
                'potential_matches': []
            }
        elif session_id == 'fake-face-match-1':
            details_dict = {
                'access_log': {
                    'session_id': session_id,
                    'timestamp': datetime.now() - timedelta(minutes=10),
                    'verification_method': 'FACE_ONLY_PENDING_REVIEW',
                    'review_status': 'pending',
                    'verification_confidence': 0.91
                },
                'employee': None,
                'verification_image_url': '/static/images/esp32Images/session_1.png',
                'potential_matches': [
                    {
                        'employee_id': 'fake-emp-1',
                        'name': 'Kaleb Cole',
                        'confidence': 0.91,
                        'photo_url': '/static/images/employees/EMP001.jpg'
                    },
                    {
                        'employee_id': 'fake-emp-2',
                        'name': 'Sebastian Galvez',
                        'confidence': 0.55,
                        'photo_url': '/static/images/employees/EMP002.jpg'
                    }
                ]
            }

        if details_dict is None:
            logger.warning(
                f"Mock details not found for session ID: {session_id}")
            flash(
                f"Mock details not found for session ID: {session_id}", "warning")
            return redirect(url_for('admin_bp.get_reviews'))

        return render_template('admin/review_details.html',
                               details=details_dict,
                               pending_count=pending_count)
        # --- End Mock Data ---

    else:
        # --- Original Database Logic ---
        logger.info(f"Fetching real data for /admin/reviews/{session_id}")
        # Validate if the provided string is a valid UUID *before* calling DB service
        try:
            session_uuid = UUID(session_id, version=4)
        except ValueError:
            logger.warning(f"Invalid UUID format received: {session_id}")
            return abort(404)  # Return 404 if not a valid UUID

        try:
            db_service: DatabaseService = current_app.db_service
            with db_service.session_scope() as session:
                # Pass the validated string UUID to the service method
                details_dict = db_service.get_session_review_details(
                    # Ensure service method gets string if needed
                    str(session_uuid))

                if details_dict is None:
                    flash(
                        f"Review details not found for session ID: {session_uuid}", "warning")
                    return redirect(url_for('admin_bp.get_reviews'))

                # Get pending count for base template
                pending_count = len(db_service.get_pending_review_sessions())

                return render_template('admin/review_details.html',
                                       details=details_dict,
                                       pending_count=pending_count)

        except Exception as e:
            logger.error(
                f"Error getting real review details for {session_uuid}: {e}", exc_info=True)
            flash(
                f"Error loading details for session {session_uuid}.", "error")
            return redirect(url_for('admin_bp.get_reviews'))
        # --- End Original Database Logic ---


@admin_bp.route('/reviews/<string:session_id>/approve', methods=['POST'])
def approve_review(session_id: str):
    """Approve access for a reviewed session."""
    logger.info(f"POST /admin/reviews/{session_id}/approve received")
    # session_id = str(session_id)
    selected_employee_id = request.form.get('selected_employee_id')

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning("Approve action disabled in mock data mode.")
        flash("Actions are disabled when using mock data.", "warning")
        return redirect(url_for('admin_bp.get_reviews'))

    # --- Original Database Logic (with UUID validation) ---
    try:
        session_uuid = UUID(session_id, version=4)
    except ValueError:
        logger.warning(f"Invalid UUID format for approve: {session_id}")
        return abort(404)

    try:
        db_service: DatabaseService = current_app.db_service
        mqtt_service: MQTTService = current_app.mqtt_service

        with db_service.session_scope() as session:
            # Use the original string representation if DB service expects it, or session_uuid
            access_log = db_service.get_access_log_by_session_id(
                session_id)

            if not access_log:
                flash(
                    # Use UUID in message
                    f"Access log not found for session {session_uuid}. Cannot approve.", "error")
                return redirect(url_for('admin_bp.get_review_details', session_id=session_id))

            # Use the actual object from DB for checks
            if access_log.verification_method == 'FACE_ONLY_PENDING_REVIEW' and not selected_employee_id:
                flash(
                    "Error: You must select an employee match to approve a Face-Only review.", "error")
                # Redirect back to details page using the original string/uuid
                return redirect(url_for('admin_bp.get_review_details', session_id=session_id))

            updated = db_service.update_review_status(
                session_id=session_id,  # Pass string if DB service expects it
                approved=True,
                employee_id=selected_employee_id  # This should be a UUID from the form
            )

            if not updated:
                flash(
                    f"Could not approve session {session_uuid}. It might not be pending or might not exist.", "warning")
            else:
                logger.info(
                    f"Session {session_uuid} approved by admin. Publishing unlock command.")
                # Pass string if MQTT service expects it
                mqtt_service._publish_unlock(session_id=session_id)
                flash(
                    f"Session {session_uuid} approved successfully.", "success")

    except Exception as e:
        logger.error(
            f"Error approving review for {session_uuid}: {e}", exc_info=True)
        flash(
            f"An error occurred while approving session {session_uuid}.", "error")

    return redirect(url_for('admin_bp.get_reviews'))


@admin_bp.route('/reviews/<string:session_id>/deny', methods=['POST'])
def deny_review(session_id: str):
    """Deny access for a reviewed session via POST, then redirect."""
    logger.info(f"POST /admin/reviews/{session_id}/deny received")
    # session_id = str(session_id)

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning("Deny action disabled in mock data mode.")
        flash("Actions are disabled when using mock data.", "warning")
        return redirect(url_for('admin_bp.get_reviews'))

    # --- Original Database Logic (with UUID validation) ---
    try:
        session_uuid = UUID(session_id, version=4)
    except ValueError:
        logger.warning(f"Invalid UUID format for deny: {session_id}")
        return abort(404)

    try:
        db_service: DatabaseService = current_app.db_service
        # Pass string if DB service expects it
        updated = db_service.update_review_status(
            session_id=session_id, approved=False)

        if not updated:
            flash(
                f"Could not deny session {session_uuid}. It might not be pending or might not exist.", "warning")
        else:
            logger.info(f"Session {session_uuid} denied by admin.")
            flash(f"Session {session_uuid} denied successfully.", "success")

    except Exception as e:
        logger.error(
            f"Error denying review for {session_uuid}: {e}", exc_info=True)
        flash(
            f"An error occurred while denying session {session_uuid}.", "error")

    return redirect(url_for('admin_bp.get_reviews'))


@admin_bp.route('/employees', methods=['GET'])
def employees_list():
    """Display a list of all employees."""
    logger.info("GET /admin/employees received")

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning("Serving mock data for /admin/employees")

        # --- Mock Data Generation ---
        fake_employees = [
            {'id': 'fake-emp-1', 'name': 'Kaleb Cole', 'role': 'Administrator', 'email': 'kaleb@example.com',
                'rfid_tag': 'EMP001-FAKE', 'active': True, 'photo_url': '/static/images/employees/EMP001.jpg'},
            {'id': 'fake-emp-2', 'name': 'Sebastian Galvez', 'role': 'Security Officer', 'email': 'sebastian@example.com',
                'rfid_tag': 'EMP002-FAKE', 'active': True, 'photo_url': '/static/images/employees/EMP002.jpg'},
            {'id': 'fake-emp-3', 'name': 'Luke Reynolds', 'role': 'Tester', 'email': 'luke@example.com',
             'rfid_tag': 'EMP003-FAKE', 'active': True, 'photo_url': '/static/images/employees/EMP003.jpg'},
            {'id': 'fake-emp-4', 'name': 'Anthony Hailey', 'role': 'Developer', 'email': 'anthony@example.com',
                'rfid_tag': 'EMP004-FAKE', 'active': True, 'photo_url': '/static/images/employees/EMP004.jpg'},
            {'id': 'fake-emp-5', 'name': 'Dakota Dietz', 'role': 'Engineer', 'email': 'kyle@example.com',
                # Example inactive
                'rfid_tag': 'EMP005-FAKE', 'active': False, 'photo_url': '/static/images/employees/EMP005.jpg'},
            {'id': 'fake-emp-6', 'name': 'Griffin Holbert', 'role': 'Receptionist', 'email': 'griffin@example.com',
                # Example no photo
                'rfid_tag': 'EMP006-FAKE', 'active': True, 'photo_url': '/static/images/employees/EMP006.jpg'},
        ]
        pending_count = 2  # Fixed mock pending count for navigation badge

        return render_template('admin/employees_list.html', employees=fake_employees, pending_count=pending_count)
        # --- End Mock Data ---

    else:
        # --- Original Database Logic ---
        logger.info("Fetching real data for /admin/employees")
        try:
            db_service: DatabaseService = current_app.db_service
            # !! NOTE: Assumes get_all_employees returns objects/dicts compatible
            # !! with the employee_list.html template, including a 'photo_url'.
            # !! Bug #4 might mean this data isn't currently correct/complete.
            employees = db_service.get_all_employees(
                include_inactive=True)  # Show all for management
            # For base template
            pending_count = len(db_service.get_pending_review_sessions())
            return render_template('admin/employees_list.html', employees=employees, pending_count=pending_count)
        except Exception as e:
            logger.error(
                f"Error fetching real employee list: {e}", exc_info=True)
            flash("Failed to load employee list.", "error")
            # Render empty on error
            return render_template('admin/employees_list.html', employees=[], pending_count=0)
        # --- End Original Database Logic ---


@admin_bp.route('/employees/new', methods=['GET'])
def employees_new_form():
    """Display the form to create a new employee."""
    logger.info("GET /admin/employees/new received")
    if current_app.config.get('USE_MOCK_DATA', False):
        pending_count = 2  # Mock pending count for nav badge
    else:
        db_service: DatabaseService = current_app.db_service
        pending_count = len(db_service.get_pending_review_sessions())
    # Pass an empty dictionary or specific defaults if needed for the form template
    return render_template('admin/employee_form.html', employee=None, is_edit=False, pending_count=pending_count)


@admin_bp.route("/employees/create", methods=["POST"])
def employees_create():
    """Create a new employee, uploading photo to Supabase if provided."""
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

        # Variables
        face_embedding = None
        photo_storage_url = None

        try:
            # Handle photo upload, embedding generation, and Supabase upload
            if photo and photo.filename and allowed_file(photo.filename):
                try:
                    # Read photo data
                    photo_data = photo.read()
                    photo.seek(0)  # Reset pointer after read

                    # Generate face embedding
                    photo_base64 = base64.b64encode(photo_data).decode('utf-8')
                    mime_type = photo.mimetype or 'image/jpeg'
                    photo_base64_uri = f"data:{mime_type};base64,{photo_base64}"
                    logger.info(
                        f"Generating face embedding for new employee {name}")
                    face_embedding = face_client.get_embedding(
                        photo_base64_uri)
                    if face_embedding:
                        logger.info("Successfully generated face embedding")
                    else:
                        logger.warning("Failed to generate face embedding")
                        flash(
                            "Could not generate face embedding from the photo.", "warning")

                    # --- Upload to Supabase ---
                    # Unique filename including the folder path
                    supabase_filename = f"employees/employee_{str(uuid.uuid4())}_profile.jpg"
                    logger.info(
                        f"Uploading photo to Supabase as {supabase_filename}")
                    photo_storage_url = upload_image_to_supabase(
                        photo_data, supabase_filename)
                    if photo_storage_url:
                        logger.info(
                            f"Photo uploaded to Supabase: {photo_storage_url}")
                    else:
                        logger.error("Failed to upload photo to Supabase.")
                        flash("Failed to save photo to cloud storage.", "error")
                        # Decide if creation should fail? Maybe proceed without photo?
                        # For now, proceed, photo_storage_url will be None.
                    # --------------------------

                except Exception as process_err:
                    logger.error(
                        f"Error processing photo/embedding/upload: {process_err}", exc_info=True)
                    flash(
                        "Failed to process the photo. Employee will be created without photo/face ID.", "warning")
                    photo_storage_url = None  # Ensure URL is None on error
                    face_embedding = None
            else:  # Handle case where no photo was uploaded
                logger.info(
                    f"No photo uploaded during creation of employee {name}.")
                photo_storage_url = None
                face_embedding = None

            # Create employee with embedding and Supabase URL
            employee = db_service.create_employee_with_session(
                session=session,
                name=name,
                rfid_tag=rfid_tag,
                role=role,
                email=email,
                active=active,
                face_embedding=face_embedding,  # Might be None
                # Pass Supabase URL (might be None)
                photo_url=photo_storage_url
            )

            # No need to save verification image separately here unless specifically desired
            # The employee photo_url is the primary reference now.

            session.commit()

            flash(f"Employee '{name}' created successfully!", "success")
            if face_embedding:
                flash("Face recognition capability enabled.", "info")
            if photo_storage_url:
                flash("Photo uploaded successfully.", "info")
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


@admin_bp.route('/employees/<string:employee_id>/edit', methods=['GET'])
def employees_edit_form(employee_id: str):
    """Display the form to edit an existing employee."""
    logger.info(f"GET /admin/employees/{employee_id}/edit received")

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning(
            "Edit form disabled in mock data mode (can't fetch specific mock employee easily).")
        flash("Editing specific employees is disabled when using mock data.", "warning")
        return redirect(url_for('admin_bp.employees_list'))

    # --- Original Database Logic (with UUID validation) ---
    try:
        employee_uuid = UUID(employee_id, version=4)
    except ValueError:
        logger.warning(f"Invalid UUID format for edit form: {employee_id}")
        return abort(404)

    # Get real count even if mocking elsewhere
    pending_count = len(current_app.db_service.get_pending_review_sessions())

    try:
        db_service: DatabaseService = current_app.db_service
        employee = db_service.get_employee_by_id(employee_uuid)  # Use UUID
        if not employee:
            flash(f"Employee with ID {employee_uuid} not found.", "error")
            return redirect(url_for('admin_bp.employees_list'))

        return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count)
    except Exception as e:
        logger.error(
            f"Error loading edit form for employee {employee_uuid}: {e}", exc_info=True)
        flash("Failed to load employee edit form.", "error")
        return redirect(url_for('admin_bp.employees_list'))
    # --- End Original Database Logic ---


@admin_bp.route('/employees/<string:employee_id>/edit', methods=['POST'])
def employees_edit(employee_id: str):
    """Handle updating an existing employee, including photo upload to Supabase."""
    logger.info(f"POST /admin/employees/{employee_id}/edit received")

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning("Edit action disabled in mock data mode.")
        flash("Actions are disabled when using mock data.", "warning")
        return redirect(url_for('admin_bp.employees_list'))

    # --- Original Database Logic (with UUID validation) ---
    try:
        employee_uuid = UUID(employee_id, version=4)
    except ValueError:
        logger.warning(
            f"Invalid UUID format for edit action: {employee_id}")
        return abort(404)

    db_service: DatabaseService = current_app.db_service
    face_client: FaceRecognitionClient = current_app.face_client

    employee = db_service.get_employee_by_id(employee_uuid)  # Use UUID
    if not employee:
        flash(
            f"Employee with ID {employee_uuid} not found. Cannot update.", "error")
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
        form_data_for_template = employee.__dict__.copy()
        form_data_for_template.update(request.form.to_dict())
        return render_template('admin/employee_form.html', employee=form_data_for_template, is_edit=True, pending_count=pending_count), 400

    # Handle Photo Upload...
    photo_file = request.files.get('photo')
    new_embedding = None
    new_photo_storage_url = None

    if photo_file and photo_file.filename != '' and allowed_file(photo_file.filename):
        logger.info(f"Processing uploaded photo for employee {employee_uuid}")
        try:
            image_bytes = photo_file.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = photo_file.mimetype
            image_base64_uri = f"data:{mime_type};base64,{image_base64}"
            logger.debug(
                f"Calling face client for updated embedding for {employee_uuid}")
            new_embedding = face_client.get_embedding(image_base64_uri)
            if new_embedding:
                update_data['face_embedding'] = new_embedding
                logger.info(
                    f"New face embedding generated for employee {employee_uuid}.")
            else:
                flash(
                    "Could not generate face embedding from the uploaded photo.", "warning")

            supabase_filename = f"employees/employee_{employee_uuid}_profile_{int(time.time())}.jpg"
            logger.info(
                f"Uploading updated photo to Supabase as {supabase_filename}")
            new_photo_storage_url = upload_image_to_supabase(
                image_bytes, supabase_filename)
            if new_photo_storage_url:
                update_data['photo_url'] = new_photo_storage_url
                logger.info(
                    f"Updated photo uploaded to Supabase: {new_photo_storage_url}")
            else:
                logger.error(
                    f"Failed to upload updated photo to Supabase for employee {employee_uuid}.")
                flash("Failed to save updated photo to cloud storage.", "error")

        except FaceRecognitionClientError as e:
            logger.error(
                f"Face recognition client error for employee {employee_uuid}: {e}")
            flash(
                f"Error generating face embedding: {e}. Photo not saved.", "error")
        except Exception as e:
            logger.error(
                f"Error processing photo upload for employee {employee_uuid}: {e}", exc_info=True)
            flash("An unexpected error occurred while processing the photo.", "error")
            pending_count = len(db_service.get_pending_review_sessions())
            return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count), 500
    elif photo_file and photo_file.filename != '' and not allowed_file(photo_file.filename):
        flash("Invalid file type for photo. Please upload PNG or JPG.", "warning")
        pending_count = len(db_service.get_pending_review_sessions())
        return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count), 400

    try:
        # Pass the UUID to the update function
        updated_employee = db_service.update_employee(
            employee_uuid, update_data)

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
            f"Error updating employee in database {employee_uuid}: {e}", exc_info=True)
        flash("An unexpected error occurred while updating the employee.", "error")
        pending_count = len(db_service.get_pending_review_sessions())
        return render_template('admin/employee_form.html', employee=employee, is_edit=True, pending_count=pending_count), 500
    # --- End Original Database Logic ---


@admin_bp.route('/employees/<string:employee_id>/delete', methods=['POST'])
def employees_delete(employee_id: str):
    """Handle deleting an employee."""
    logger.info(f"POST /admin/employees/{employee_id}/delete received")

    if current_app.config.get('USE_MOCK_DATA', False):
        logger.warning("Delete action disabled in mock data mode.")
        flash("Actions are disabled when using mock data.", "warning")
        return redirect(url_for('admin_bp.employees_list'))

    # --- Original Database Logic (with UUID validation) ---
    try:
        employee_uuid = UUID(employee_id, version=4)
    except ValueError:
        logger.warning(
            f"Invalid UUID format for delete action: {employee_id}")
        return abort(404)

    try:
        db_service: DatabaseService = current_app.db_service

        # --- Fetch employee first to get photo_url BEFORE deleting ---
        employee = db_service.get_employee_by_id(
            employee_uuid)  # Fetch by UUID
        if not employee:
            flash(
                f"Employee with ID {employee_uuid} not found. Cannot delete.", "error")
            return redirect(url_for('admin_bp.employees_list'))

        # Store URL before deletion
        photo_url_to_delete = employee.photo_url
        employee_name_for_flash = employee.name  # Store name for flash message
        # -----------------------------------------------------------

        # --- Attempt to delete database record ---
        deleted = db_service.delete_employee(employee_uuid)  # Delete by UUID
        # -----------------------------------------

        if deleted:
            flash(
                f"Employee '{employee_name_for_flash}' deleted successfully from database.", "success")

            # --- Attempt to delete photo from Supabase AFTER successful DB delete ---
            if photo_url_to_delete:
                logger.info(
                    f"Attempting to delete photo from Supabase for deleted employee {employee_uuid}. URL: {photo_url_to_delete}")
                object_path = extract_object_path_from_url(photo_url_to_delete)
                if object_path:
                    delete_success = delete_image_from_supabase(object_path)
                    if delete_success:
                        logger.info(
                            f"Successfully deleted photo '{object_path}' from Supabase.")
                        # Optional: flash success for photo deletion
                    else:
                        logger.error(
                            f"Failed to delete photo '{object_path}' from Supabase for employee {employee_uuid}.")
                        flash(
                            "Employee record deleted, but failed to remove photo from storage. Check logs.", "warning")
                else:
                    logger.warning(
                        f"Could not extract valid object path from URL '{photo_url_to_delete}' for deleted employee {employee_uuid}. Skipping Supabase deletion.")
            else:
                logger.info(
                    f"No photo_url associated with deleted employee {employee_uuid}. No Supabase deletion needed.")
            # ---------------------------------------------------------------------

        else:
            # Use the stored name here as employee object might be gone if delete partially failed
            flash(
                f"Failed to delete employee '{employee_name_for_flash}'. Check logs for details (e.g., dependencies).", "error")

    except Exception as e:
        logger.error(
            f"Error processing delete request for employee {employee_uuid}: {e}", exc_info=True)
        flash("An unexpected error occurred while deleting the employee.", "error")

    return redirect(url_for('admin_bp.employees_list'))
    # --- End Original Database Logic ---

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


@admin_bp.route('/api/status/emergency/reset', methods=['POST'])
def reset_emergency_status():
    """API endpoint to manually reset the emergency status."""
    current_app.emergency_active = False
    logger.warning("Emergency state manually reset to inactive via admin API")
    return jsonify({
        "success": True,
        "message": "Emergency state reset to inactive",
        "emergency_active": current_app.emergency_active,
        "timestamp": datetime.utcnow().isoformat()
    })
