
from flask import Blueprint, request, jsonify
from models.notifications import Notification, NotificationType, SeverityLevel
from utils.notifications import send_notification, send_sms_notification
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


@mock_bp.route("/mock/send_sms", methods=['POST'])
def test_send_sms():
    """
    Simulate sending an SMS notification.

    Endpoint:
        POST /mock/send_sms

    Description:
        This endpoint simulates sending an SMS notification using the send_sms_notification function.

    Request Body:
        The request body should be a JSON object containing the following fields:
        - phone_number: The phone number to which the SMS should be sent.
        - message: The message content of the SMS.

    Example Request:
        curl -X POST http://localhost:5000/mock/send_sms \
        -H "Content-Type: application/json" \
        -d '{
          "phone_number": "+1234567890",
          "message": "Test SMS message"
        }'

    Example Request Body:
        {
          "phone_number": "+1234567890",
          "message": "Test SMS message"
        }

    Response:
        The response will be a JSON object indicating the success or failure of the SMS sending operation.

        Success Response:
            {
              "status": "success",
              "message": "Test SMS sent"
            }

        Error Response:
            {
              "status": "error",
              "message": "Error message describing what went wrong"
            }
    """
    # data = request.get_json()
    # phone_number = data.get('phone_number', '+1234567890')
    # message = data.get('message', 'Default test SMS message')
    message = "Test SMS message"

    notification = Notification(
        # TODO: Change to SMS notification type
        notification_type=NotificationType.SYSTEM_ALERT, # TODO: Change to SMS notification type
        severity_level=SeverityLevel.INFO,
        rfid_id="TEST_RFID_123",
        face_id="TEST_FACE_123",
        message=message,
        image_url=""
    )

    try:
        send_sms_notification(notification)
        return jsonify({"status": "success", "message": "Test SMS sent"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
