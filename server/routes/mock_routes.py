
from flask import Blueprint, request, jsonify
from models.notifications import Notification, NotificationType, SeverityLevel
from utils.notifications import send_notification
import json
import uuid


mock_bp = Blueprint('mock', __name__)


@mock_bp.route("/mock/face_recognition", methods=['POST'])
def test_recognition():
    """Simulate facial recognition flow triggered by button press"""
    # Simulate a successful recognition
    notification = Notification(
        notification_type=NotificationType.FACE_RECOGNIZED,
        severity_level=SeverityLevel.INFO,
        rfid_id="TEST_RFID_123",
        face_id="TEST_FACE_123",
        message="Test facial recognition successful",
        image_url="https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/user-entries/d6797d9a-e52b-4ee4-9161-14243e3e6eb2.jpg"
    )

    try:
        send_notification(notification)
        return jsonify({"status": "success", "message": "Test notification sent"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
