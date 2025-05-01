"""Custom Jinja filters for the Flask application."""


def format_verification_method(method: str) -> str:
    """Convert verification method codes to human-readable format."""
    method_map = {
        'RFID_ONLY_PENDING_REVIEW': 'RFID Only',
        'FACE_ONLY_PENDING_REVIEW': 'Face Only',
        'FACE_VERIFICATION_FAILED': 'Face Verification Failed',
        'RFID+FACE': 'RFID + Face',
        'ERROR': 'System Error',
        'NO_FACE_OR_RFID': 'No Face or RFID Detected',
        'NONE': 'None'
    }
    return method_map.get(method, method)  # Return original if not in map
