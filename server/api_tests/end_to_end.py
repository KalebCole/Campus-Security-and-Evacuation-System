import os
import sys
import time
import requests
import cv2
import numpy as np

# Add server directory to path for imports
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)

# Test configuration
BASE_URL = "http://localhost:5000/api"
TEST_RFID = "123456"  # Bob's RFID from mock DB
TEST_IMAGE = "test_images/bob.jpg"
SESSION_ID = "1"


def run_test():
    """Simple end-to-end verification test"""
    print("\n=== 🧪 STARTING VERIFICATION TEST ===\n")

    # Step 1: Activate system
    print("1. Activating system...")
    requests.get(f"{BASE_URL}/activate")

    # Step 2: Send RFID
    print(f"2. Sending RFID tag: {TEST_RFID}")
    rfid_response = requests.post(
        f"{BASE_URL}/rfid", json={"rfid_tag": TEST_RFID, "session_id": SESSION_ID})

    if rfid_response.status_code not in [200, 202]:
        print(f"❌ RFID submission failed: {rfid_response.text}")
        return

    session_id = rfid_response.json().get("session_id")
    print(f"✅ RFID accepted! Session ID: {session_id}")

    # Step 3: Create test image if it doesn't exist
    if not os.path.exists(TEST_IMAGE):
        print("Creating test image...")
        os.makedirs(os.path.dirname(TEST_IMAGE), exist_ok=True)
        dummy_img = np.ones((300, 300, 3), dtype=np.uint8) * 255  # White image
        cv2.imwrite(TEST_IMAGE, dummy_img)

    # Step 4: Send image
    print("3. Sending image...")
    with open(TEST_IMAGE, 'rb') as image_file:
        files = {'imageFile': ('face.jpg', image_file, 'image/jpeg')}
        data = {'session_id': session_id}
        image_response = requests.post(
            f"{BASE_URL}/image",
            files=files,
            data=data
        )

    if image_response.status_code not in [200, 202]:
        print(f"❌ Image submission failed: {image_response.text}")
    else:
        print(f"✅ Image accepted!")

    # Step 5: Wait for verification processing
    print("\n4. Waiting for worker to process verification...")
    for i in range(5):
        print(f"   Checking status... ({i+1}/5)")
        status_response = requests.get(f"{BASE_URL}/status/{session_id}")

        # If 404, session was removed by worker (success)
        if status_response.status_code == 404:
            print("✅ Session processed and removed by worker")
            break

        # If still there, wait a bit
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"   Current status: {status.get('session_type')}")

        time.sleep(1)

    # Step 6: Deactivate system
    print("\n5. Deactivating system...")
    requests.get(f"{BASE_URL}/deactivate")

    print("\n=== 🎉 TEST COMPLETE ===\n")


if __name__ == "__main__":
    run_test()
