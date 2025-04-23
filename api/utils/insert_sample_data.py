"""Utility script to insert sample verification images into the database."""

from utils.generate_sample_images import save_sample_images
from services.database import DatabaseService
from config import Config
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import random

# Add the parent directory to the Python path so we can import our app modules
sys.path.append(str(Path(__file__).parent.parent))


def insert_sample_data():
    """Insert sample verification images and access logs into the database."""
    # Initialize database service with local database URL
    db_url = 'postgresql://cses_admin:cses_password_123!@localhost:5432/cses_db'
    db_service = DatabaseService(db_url)

    # First, get some sample images
    print("Downloading sample images...")
    image_data = save_sample_images(num_images=5)

    # Get existing employees from the database
    try:
        employees = db_service.get_all_employees()
        if not employees:
            print("No employees found in database. Please add some employees first.")
            return
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Please make sure your PostgreSQL server is running and accessible.")
        return

    print("\nInserting sample verification data...")

    # Different verification methods to simulate
    verification_methods = [
        'RFID_ONLY_PENDING_REVIEW',
        'FACE_ONLY_PENDING_REVIEW',
        'FACE_VERIFICATION_FAILED',
        'RFID+FACE'
    ]

    # Create some sample sessions over the past few days
    for i, image in enumerate(image_data):
        # Generate a random timestamp within the last 7 days
        timestamp = datetime.utcnow() - timedelta(
            days=random.randint(0, 7),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        # Generate a session ID
        session_id = str(uuid.uuid4())

        # Randomly select a verification method
        method = random.choice(verification_methods)

        # Randomly select an employee
        employee = random.choice(employees)

        # Read the image data
        with open(image['file_path'], 'rb') as f:
            image_bytes = f.read()

        # Save the verification image
        verification_image = db_service.save_verification_image(
            session_id=session_id,
            # Use a dummy Supabase URL format
            storage_url=f"sample/verification_images/session_{session_id}.jpg",
            device_id='SAMPLE_DEVICE_001',
            matched_employee_id=employee.id if method != 'FACE_ONLY_PENDING_REVIEW' else None,
            processed=True
        )

        # Determine if access should be granted
        access_granted = method == 'RFID+FACE'
        review_status = 'approved' if access_granted else 'pending'

        # Log the access attempt
        db_service.log_access_attempt(
            session_id=session_id,
            verification_method=method,
            access_granted=access_granted,
            employee_id=employee.id if method != 'FACE_ONLY_PENDING_REVIEW' else None,
            verification_confidence=0.85 if access_granted else 0.45,
            review_status=review_status
        )

        print(
            f"Created sample access log {i+1}: Method={method}, Employee={employee.name}")

    print("\nSample data insertion complete!")


if __name__ == "__main__":
    insert_sample_data()
