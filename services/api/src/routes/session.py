from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import Dict, Any
from ..models.session import Session
from ..services.database import DatabaseService, SessionRecord
from ..core.config import Config
import uuid

bp = Blueprint('session', __name__, url_prefix='/api/sessions')
db_service = None  # Will be initialized in app.py


def init_db_service(connection_string: str):
    """Initialize database service."""
    global db_service
    db_service = DatabaseService(connection_string)


@bp.route('/active', methods=['GET'])
def get_active_sessions():
    """Get all active sessions."""
    if not db_service:
        return jsonify({'error': 'Database service not initialized'}), 500

    try:
        sessions = db_service.get_active_sessions()
        return jsonify([{
            'id': str(session.id),
            'device_id': session.device_id,
            'state': session.state,
            'start_time': session.start_time.isoformat(),
            'last_update': session.last_update.isoformat(),
            'face_detected': session.face_detected,
            'rfid_detected': session.rfid_detected
        } for session in sessions])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """Get session details by ID."""
    if not db_service:
        return jsonify({'error': 'Database service not initialized'}), 500

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        return jsonify({'error': 'Invalid session ID'}), 400

    try:
        session = db_service.Session()
        record = session.query(SessionRecord).filter(
            SessionRecord.id == session_uuid).first()
        if not record:
            return jsonify({'error': 'Session not found'}), 404

        return jsonify({
            'id': str(record.id),
            'device_id': record.device_id,
            'state': record.state,
            'start_time': record.start_time.isoformat(),
            'last_update': record.last_update.isoformat(),
            'face_detected': record.face_detected,
            'rfid_detected': record.rfid_detected,
            'is_expired': record.is_expired
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/update', methods=['POST'])
def update_session():
    """Update session state."""
    if not db_service:
        return jsonify({'error': 'Database service not initialized'}), 500

    try:
        data = request.get_json()
        session = Session(**data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    try:
        session_id = uuid.UUID(session.session_id)
    except ValueError:
        return jsonify({'error': 'Invalid session ID'}), 400

    try:
        record = db_service.update_session(
            session_id=session_id,
            state=session.state,
            face_detected=session.face_detected,
            rfid_detected=session.rfid_detected
        )

        if not record:
            return jsonify({'error': 'Session not found'}), 404

        return jsonify({
            'id': str(record.id),
            'state': record.state,
            'last_update': record.last_update.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
